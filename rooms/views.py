# rooms/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Count

from .models import Course, Thread, Post, Session
from messaging.models import MessageThread, Message
from messaging.utils import get_or_create_message_thread
from messaging.constants import SESSION_INVITE_PREFIX
from .forms import ThreadForm, PostForm, SessionCreateForm
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from core.utils import get_online_user_ids

# Helper function to get a user's invite count
def get_pending_invites_count(user):
    return Message.objects.filter(
        thread__participants=user,
        content__startswith='SESSION_INVITE::'
    ).exclude(sender=user).count()

@login_required
def course_list_view(request):
    courses = Course.objects.exclude(slug='hang-out')
    return render(request, 'rooms/course_list.html', {'courses': courses})

@login_required
def course_detail_view(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.course = course
            thread.author = request.user
            thread.save()
            Post.objects.create(thread=thread, content=form.cleaned_data['content'], author=request.user)
            channel_layer = get_channel_layer()
            html = render_to_string("rooms/partials/thread_item.html", {'thread': thread, 'course': course})
            async_to_sync(channel_layer.group_send)( f'course_room_{course.slug}', { 'type': 'broadcast_message', 'html': html, 'message_type': 'new_thread' } )
            return redirect('thread_detail', slug=course.slug, pk=thread.pk)
    threads = course.threads.all()
    form = ThreadForm()
    context = { 'course': course, 'threads': threads, 'form': form, }
    return render(request, 'rooms/course_detail.html', context)

@login_required
def thread_detail_view(request, slug, pk):
    thread = get_object_or_404(Thread, pk=pk, course__slug=slug)
    posts = thread.posts.order_by('created_at')
    original_post = posts.first()
    replies = posts[1:]
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.thread = thread
            post.author = request.user
            post.save()
            channel_layer = get_channel_layer()
            html = render_to_string("rooms/partials/post_item.html", {'post': post})
            async_to_sync(channel_layer.group_send)( f'course_room_{slug}', { 'type': 'broadcast_message', 'html': html, 'message_type': 'new_post' } )
            return redirect('thread_detail', slug=slug, pk=pk)
    form = PostForm()
    context = { 'thread': thread, 'original_post': original_post, 'replies': replies, 'form': form, }
    return render(request, 'rooms/thread_detail.html', context)

@login_required
def edit_post_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author: return HttpResponseForbidden()
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return render(request, 'rooms/partials/post_item.html', {'post': post})
    else:
        form = PostForm(instance=post)
        return render(request, 'rooms/partials/edit_post_form.html', {'form': form, 'post': post})

@login_required
@require_POST
def delete_post_view(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user != post.author: return HttpResponseForbidden()
    if post.thread.posts.count() == 1:
        thread = post.thread
        course = thread.course
        thread.delete()
        return redirect('course_detail', slug=course.slug)
    post.delete()
    return HttpResponse('')

@login_required
def create_session_view(request):
    if request.method == 'POST':
        form = SessionCreateForm(request.POST, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.host = request.user
            session.save()
            session.participants.add(request.user)
            
            invited_buddies = form.cleaned_data.get('buddies_to_invite')
            all_participants = [request.user] + list(invited_buddies)
            thread = get_or_create_message_thread(all_participants)
            
            # Uses the constant to build the invite string
            invite_content = f"{SESSION_INVITE_PREFIX}{session.id}::{request.user.first_name} invited you to a session for {session.course.name} on the topic: {session.topic}"
            new_message = Message.objects.create(thread=thread, sender=request.user, content=invite_content)
            
            channel_layer = get_channel_layer()
            
            room_group_name = f'chat_{thread.id}'
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'chat_message',
                    'message': new_message.content,
                    'sender_id': request.user.id,
                    'sender_first_name': request.user.first_name,
                }
            )
            
            for buddy in invited_buddies:
                group_name = f'notifications_for_user_{buddy.pk}'
                message = {
                    'type': 'send_notification',
                    'message': {
                        'text': f'{request.user.first_name} invited you to a new session!',
                        'invite_count': get_pending_invites_count(buddy)
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message)

            return redirect('conversation', thread_id=thread.pk)
    else:
        form = SessionCreateForm(user=request.user)
    return render(request, 'rooms/create_session.html', {'form': form})

@login_required
@require_POST
def accept_session_invite(request, session_id, message_id):
    session = get_object_or_404(Session, pk=session_id)
    message = get_object_or_404(Message, pk=message_id)
    session.participants.add(request.user)
    message.content = f"{request.user.first_name} accepted the invite."
    message.save()
    channel_layer = get_channel_layer()
    group_name = f'notifications_for_user_{request.user.pk}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'message': {'invite_count': get_pending_invites_count(request.user)}
        }
    )
    return render(request, 'messaging/partials/message_content.html', {'message': message})

@login_required
@require_POST
def decline_session_invite(request, session_id, message_id):
    message = get_object_or_404(Message, pk=message_id)
    message.content = f"{request.user.first_name} declined the invite."
    message.save()
    channel_layer = get_channel_layer()
    group_name = f'notifications_for_user_{request.user.pk}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'message': {'invite_count': get_pending_invites_count(request.user)}
        }
    )
    return render(request, 'messaging/partials/message_content.html', {'message': message})

@login_required
def session_detail_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.user not in session.participants.all():
        return HttpResponseForbidden("You are not a participant of this session.")
    online_user_ids = get_online_user_ids()
    context = {'session': session, 'online_user_ids': online_user_ids, }
    return render(request, 'rooms/session_detail.html', context)

@login_required
@require_POST
def delete_session_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.user != session.host:
        return HttpResponseForbidden()
    session.delete()
    return redirect('sessions')

@login_required
@require_POST
def leave_session_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    session.participants.remove(request.user)
    return redirect('sessions')

@login_required
def session_participants_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.user not in session.participants.all():
        return HttpResponseForbidden()
    online_user_ids = get_online_user_ids()
    context = {'session': session, 'online_user_ids': online_user_ids}
    return render(request, 'rooms/partials/participant_list.html', context)
