# accounts/services.py

from django.contrib.auth import get_user_model
from .models import BuddyRequest, SkippedMatch

User = get_user_model()

def find_matches(user):
    """
    Finds potential matches for a given user, excluding existing buddies,
    pending requests, and permanently skipped users.
    """
    user_courses = user.courses.all()

    # Get IDs of all users to exclude
    buddies_ids = user.buddies.all().values_list('id', flat=True)
    sent_requests_ids = BuddyRequest.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    received_requests_ids = BuddyRequest.objects.filter(to_user=user).values_list('from_user_id', flat=True)
    skipped_ids = SkippedMatch.objects.filter(from_user=user).values_list('skipped_user_id', flat=True)

    # Combine all IDs to exclude into a single set for efficiency
    exclude_ids = set(list(buddies_ids)) | \
                set(list(sent_requests_ids)) | \
                set(list(received_requests_ids)) | \
                set(list(skipped_ids)) | \
                {user.id}

    # Find potential matches who share at least one course and are not in the exclusion list
    potential_matches = User.objects.filter(courses__in=user_courses) \
                                .exclude(id__in=exclude_ids) \
                                .distinct()

    # Score the remaining matches
    matches_with_scores = []
    for match in potential_matches:
        score = 0
        shared_courses = set(user_courses) & set(match.courses.all())
        shared_academic_courses = [course for course in shared_courses if course.slug != 'hang-out']

        if shared_courses:
            score += 60 * len(shared_courses)

        if user.age and match.age and abs(user.age - match.age) <= 2:
            score += 10

        if score > 0:
            matches_with_scores.append({
                'user': match,
                'score': score,
                'shared_courses': shared_academic_courses,
            })

    # Sort matches by score, highest first
    return sorted(matches_with_scores, key=lambda k: k['score'], reverse=True)
