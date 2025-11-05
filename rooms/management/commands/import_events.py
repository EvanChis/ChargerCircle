# rooms/management/commands/import_events.py

import requests
import xml.etree.ElementTree as ET  # For parsing RSS (XML)
import re                           # For cleaning RSS data
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rooms.models import Course, Thread, Post
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from urllib.parse import urlparse
import os.path
from django.utils.html import strip_tags

# Uses both data sources
EVENTS_RSS_URL = "https://uah.campuslabs.com/engage/events.rss"
BASE_EVENTS_API_URL = "https://uah.campuslabs.com/engage/api/discovery/event/search"
IMAGE_BASE_URL = "https://uah.campuslabs.com"

User = get_user_model()

class Command(BaseCommand):
    help = 'Uses RSS feed to get current events, then uses JSON API to get event details and images.'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Starting Hybrid Event Import ---")

        # --- Step 1: Find the "Events" Course and the "System" User ---
        try:
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                self.stdout.write(self.style.ERROR("No superuser found. Please create one."))
                return
            self.stdout.write(f"Using user '{system_user.email}' as author.")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("No superuser found. Please create one."))
            return

        try:
            events_course = Course.objects.get(slug='events')
            self.stdout.write(f"Found course: '{events_course.name}'")
        except Course.DoesNotExist:
            self.stdout.write(self.style.ERROR("'events' course not found. Did you create it in the admin panel?"))
            return
            
        # --- Step 2: Scrape the UAH Events RSS Feed ---
        self.stdout.write(f"Fetching events from RSS: {EVENTS_RSS_URL}...")
        try:
            response = requests.get(EVENTS_RSS_URL)
            response.raise_for_status() 
            root = ET.fromstring(response.content)
            
            all_events = root.findall('./channel/item')
            self.stdout.write(f"Found {len(all_events)} total events in RSS.")
            
            event_list = all_events[:25] # Only take the first 25
            self.stdout.write(f"Processing the 25 most recent events...")
            
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch from RSS: {e}"))
            return
        except ET.ParseError as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse XML: {e}"))
            return

        # --- Step 3: Loop Through Events and Add to Database ---
        new_events_count = 0
        for rss_event in event_list:
            try:
                # Get base data from RSS
                event_title = rss_event.find('title').text.strip()
                rss_description_html = rss_event.find('description').text
                
                # Get the link to the original event page
                event_url = rss_event.find('link').text.strip()

                # Check if a thread with this title already exists
                if Thread.objects.filter(title=event_title, course=events_course).exists():
                    self.stdout.write(self.style.WARNING(f"Skipping '{event_title}', it already exists."))
                    continue

                # Set defaults
                final_image_url = ""
                event_date = "Date not specified."
                event_description = "No description provided."

                # --- Step 4: Query the JSON API to get the data ---
                try:
                    self.stdout.write(f"Querying API for '{event_title}'...")
                    params = {"take": 1, "query": event_title}
                    json_response = requests.get(BASE_EVENTS_API_URL, params=params)
                    json_response.raise_for_status()
                    json_data = json_response.json()

                    if not json_data.get('value') or len(json_data['value']) == 0:
                        raise Exception("API returned no event for this title.")
                    
                    # Found a match. Uses the JSON data
                    api_data = json_data['value'][0]

                    # 1. Get Image
                    if api_data.get('imagePath'):
                        source_image_url = f"{IMAGE_BASE_URL}/{api_data['imagePath']}"
                        image_response = requests.get(source_image_url)
                        image_response.raise_for_status()
                        
                        image_content = ContentFile(image_response.content)
                        parsed_path = urlparse(source_image_url).path
                        image_name = os.path.basename(parsed_path)

                        s3_file_path = f'event_images/{image_name}'
                        default_storage.save(s3_file_path, image_content)
                        final_image_url = default_storage.url(s3_file_path)
                    
                    # 2. Get Date
                    if api_data.get('startsOn'):
                        starts_on = datetime.fromisoformat(api_data['startsOn'])
                        event_date = starts_on.strftime("%A, %B %d, %Y at %#I:%M %p")

                    # 3. Get Description
                    if api_data.get('description'):
                        event_description = api_data['description'].strip()

                except Exception as api_e:
                    self.stdout.write(self.style.WARNING(f"API query failed for '{event_title}': {api_e}"))
                    self.stdout.write(self.style.WARNING(f"Falling back to text-only RSS data for this event."))
                    # --- Fallback to RSS data ---
                    try:
                        date_match = re.search(r'<strong>When:</strong>\s*([^<]+)<', rss_description_html, re.IGNORECASE)
                        if date_match: event_date = date_match.group(1).strip()
                        
                        parts = re.split(r'<hr\s*/?>', rss_description_html, maxsplit=1, flags=re.IGNORECASE)
                        if len(parts) > 1: event_description = strip_tags(parts[1]).strip()
                    except Exception:
                        pass # Keep defaults
                
                # --- Step 5: Create the Post ---
                new_thread = Thread.objects.create(
                    course=events_course,
                    title=event_title,
                    author=system_user
                )
                
                # --- MODIFIED CONTENT ---
                post_content = f"""
<img src="{final_image_url}" alt="" style="max-width: 100%; height: auto; border-radius: 8px; margin-bottom: 1rem;">
<p><strong>When:</strong> {event_date}</p>
<a href="{event_url}" target="_blank" class="button" style="text-decoration: none; margin-bottom: 1rem; display: inline-block;">
    View Original Event
</a>
<hr>
<p>{event_description}</p>
                """
                # --- END MODIFIED CONTENT ---
                
                Post.objects.create(
                    thread=new_thread,
                    content=post_content.strip(),
                    author=system_user
                )
                new_events_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not parse event '{event_title}': {e}"))

        self.stdout.write(self.style.SUCCESS(f"--- Import Complete: Added {new_events_count} new events. ---"))
