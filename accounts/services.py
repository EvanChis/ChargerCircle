# accounts/services.py

from django.contrib.auth import get_user_model
from .models import SkippedMatch, Like

User = get_user_model()

def find_matches(user):
    
    INTEREST_WEIGHT = 100
    COURSE_WEIGHT = 60
    AGE_BONUS = 10
    
    user_all_tags = user.courses.all()
    user_interests = set(user_all_tags.filter(tag_type='interest'))
    user_courses = set(user_all_tags.filter(tag_type='course'))

    buddies_ids = user.buddies.all().values_list('id', flat=True)
    likes_given_ids = Like.objects.filter(from_user=user).values_list('to_user_id', flat=True)
    skipped_ids = SkippedMatch.objects.filter(from_user=user).values_list('skipped_user_id', flat=True)

    exclude_ids = set(list(buddies_ids)) | \
                set(list(likes_given_ids)) | \
                set(list(skipped_ids)) | \
                {user.id}

    # Get preferences
    my_min_age = user.profile.match_age_min
    my_max_age = user.profile.match_age_max

    # Initial filter: shared courses + exclude IDs + basic age check (they fit MY range)
    potential_matches = User.objects.filter(courses__in=user_all_tags) \
                                .exclude(id__in=exclude_ids) \
                                .filter(age__gte=my_min_age, age__lte=my_max_age) \
                                .select_related('profile') \
                                .prefetch_related('profile__images', 'courses') \
                                .distinct()

    matches_with_scores = []
    for match in potential_matches:
        # MUTUAL CHECK: Do I fit THEIR range?
        if match.profile.match_age_min > user.age or match.profile.match_age_max < user.age:
            continue

        score = 0
        match_all_tags = match.courses.all()
        match_interests = set(match_all_tags.filter(tag_type='interest'))
        match_courses = set(match_all_tags.filter(tag_type='course'))
        
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
                'shared_tags': list(shared_interests) + list(shared_courses),
            })

    return sorted(matches_with_scores, key=lambda k: k['score'], reverse=True)
