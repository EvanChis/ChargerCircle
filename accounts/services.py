# accounts/services.py

# Import get_user_model from django.contrib.auth because we need to query the main 'User' model.
from django.contrib.auth import get_user_model
# Import SkippedMatch, Like from .models because 'find_matches' needs them to exclude users.
from .models import SkippedMatch, Like

User = get_user_model()

"""
Author:
This function is the core logic for the "Discover" page. It
finds a list of potential buddies for the user. It works by:
1. Finding all users who share at least one course.
2. Filtering out people the user has already buddied with,
   liked, or skipped.
3. Scoring the remaining people based on shared courses and
   similar age.
4. Returning a final list, sorted with the best matches first.
RT: This function is called by the HTMX views every time a
user "likes" or "skips" someone on the Discover page.
"""
def find_matches(user):
    
    # Finds potential matches for a given user, excluding existing buddies,
    # users they have already liked, and permanently skipped users.
    
    user_courses = user.courses.all()

    # Gets IDs of all users to exclude
    buddies_ids = user.buddies.all().values_list('id', flat=True)
    likes_given_ids = Like.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    skipped_ids = SkippedMatch.objects.filter(from_user=user).values_list('skipped_user_id', flat=True)

    # Combines all IDs to exclude into a single set for efficiency
    exclude_ids = set(list(buddies_ids)) | \
                set(list(likes_given_ids)) | \
                set(list(skipped_ids)) | \
                {user.id}

    # Finds potential matches and pre-fetch related data to prevent extra queries
    potential_matches = User.objects.filter(courses__in=user_courses) \
                                .exclude(id__in=exclude_ids) \
                                .select_related('profile') \
                                .prefetch_related('profile__images', 'courses') \
                                .distinct()

    # Scores the remaining matches
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

    # Sorts matches by score, highest first
    return sorted(matches_with_scores, key=lambda k: k['score'], reverse=True)

