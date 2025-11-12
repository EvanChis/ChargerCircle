# accounts/services.py

# Import get_user_model from django.contrib.auth because we need to query the main 'User' model.
from django.contrib.auth import get_user_model
# Import SkippedMatch, Like from .models because 'find_matches' needs them to exclude users.
from .models import SkippedMatch, Like

User = get_user_model()

"""
Author: Evan
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
    
    # Define weights
    INTEREST_WEIGHT = 100 # Interests are weighted higher
    COURSE_WEIGHT = 60
    AGE_BONUS = 10
    
    # Get user's tags, split by type
    user_all_tags = user.courses.all()
    user_interests = set(user_all_tags.filter(tag_type='interest'))
    user_courses = set(user_all_tags.filter(tag_type='course'))

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
    # The initial filter is still good - it finds anyone sharing *any* tag.
    potential_matches = User.objects.filter(courses__in=user_all_tags) \
                                .exclude(id__in=exclude_ids) \
                                .select_related('profile') \
                                .prefetch_related('profile__images', 'courses') \
                                .distinct()

    # Scores the remaining matches
    matches_with_scores = []
    for match in potential_matches:
        score = 0
        
        # Get match's tags, split by type
        match_all_tags = match.courses.all()
        match_interests = set(match_all_tags.filter(tag_type='interest'))
        match_courses = set(match_all_tags.filter(tag_type='course'))
        
        # Calculate shared tags
        shared_interests = user_interests & match_interests
        shared_courses = user_courses & match_courses

        if shared_interests:
            score += (INTEREST_WEIGHT * len(shared_interests))

        if shared_courses:
            score += (COURSE_WEIGHT * len(shared_courses))

        if user.age and match.age and abs(user.age - match.age) <= 2:
            score += AGE_BONUS

        if score > 0:
            matches_with_scores.append({
                'user': match,
                'score': score,
                # Combine shared tags to display on the card
                'shared_tags': list(shared_interests) + list(shared_courses),
            })

    # Sorts matches by score, highest first
    return sorted(matches_with_scores, key=lambda k: k['score'], reverse=True)
