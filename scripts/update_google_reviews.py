"""Refresh the Google reviews block on index.html from the Google Places API (New).

Reads GOOGLE_PLACES_API_KEY and GOOGLE_PLACE_ID from the environment.
Replaces everything between <!-- GOOGLE_REVIEWS:START --> and <!-- GOOGLE_REVIEWS:END -->
in index.html. If the API call fails, the file is left unchanged and the script exits non-zero.
"""
import html
import json
import os
import re
import sys
import urllib.request
import urllib.parse

PAGE = os.path.join(os.path.dirname(__file__), '..', 'index.html')
MAX_CARDS = 3
MIN_RATING = 1  # set to 4 to show only 4-5 star reviews

API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY', '').strip()
PLACE_ID = os.environ.get('GOOGLE_PLACE_ID', '').strip()
if not API_KEY or not PLACE_ID:
    sys.exit('Missing GOOGLE_PLACES_API_KEY or GOOGLE_PLACE_ID')

FIELDS = ','.join([
    'reviews.rating', 'reviews.text', 'reviews.relativePublishTimeDescription',
    'reviews.publishTime', 'reviews.authorAttribution',
])
req = urllib.request.Request(
    'https://places.googleapis.com/v1/places/' + urllib.parse.quote(PLACE_ID),
    headers={'X-Goog-Api-Key': API_KEY, 'X-Goog-FieldMask': FIELDS},
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode('utf-8'))
except Exception as e:  # keep the existing page if the API is unavailable
    sys.exit('Places API request failed: %s' % e)

reviews = [
    rv for rv in data.get('reviews', [])
    if int(rv.get('rating', 0)) >= MIN_RATING and (rv.get('text') or {}).get('text')
]
reviews.sort(key=lambda rv: rv.get('publishTime', ''), reverse=True)
reviews = reviews[:MAX_CARDS]
if not reviews:
    sys.exit('No reviews returned; leaving page unchanged')

cards = []
delays = ['0.00s', '0.08s', '0.16s']
for i, rv in enumerate(reviews):
    rating = int(rv.get('rating', 5))
    author = rv.get('authorAttribution', {})
    name = html.escape(author.get('displayName', 'Google reviewer'))
    text = html.escape(rv['text']['text'])
    when = html.escape(rv.get('relativePublishTimeDescription', ''))
    stars = '★' * rating + '☆' * (5 - rating)
    cards.append(
        '        <div class="reveal-up" style="background:#111111;padding:32px;border-left:3px solid #0154b1;transition-delay:%s;">\n'
        '          <div style="display:flex;gap:2px;margin:0 0 14px;color:#e8a33d;font-size:15px;letter-spacing:1px;" aria-label="%d out of 5 stars">%s</div>\n'
        '          <p style="font-size:15.5px;line-height:1.65;color:#dfe3e6;margin:0 0 20px;">&ldquo;%s&rdquo;</p>\n'
        '          <div style="font-weight:700;font-size:14.5px;color:#fff;">%s</div>\n'
        '          <div style="color:#8a857d;font-size:13.5px;">Google review%s</div>\n'
        '        </div>' % (delays[i], rating, stars, text, name, (' &middot; ' + when) if when else '')
    )
cards.append(
    '        <div style="grid-column:1/-1;text-align:center;">'
    '<a href="https://search.google.com/local/reviews?placeid=%s" target="_blank" rel="noopener noreferrer" '
    'style="color:#4a90e2;font-weight:700;font-size:15px;text-decoration:none;">See all reviews on Google &rarr;</a></div>'
    % html.escape(PLACE_ID)
)
block = '\n' + '\n'.join(cards) + '\n      '

with open(PAGE, encoding='utf-8') as f:
    page = f.read()
pattern = re.compile(r'<!-- GOOGLE_REVIEWS:START -->.*?<!-- GOOGLE_REVIEWS:END -->', re.S)
if not pattern.search(page):
    sys.exit('Markers not found in index.html')
new_page = pattern.sub(lambda m: '<!-- GOOGLE_REVIEWS:START -->' + block + '<!-- GOOGLE_REVIEWS:END -->', page, count=1)
with open(PAGE, 'w', encoding='utf-8') as f:
    f.write(new_page)
print('Updated with %d review(s)' % len(reviews))
