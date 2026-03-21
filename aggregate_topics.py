import json

# Load the original topics
with open('topics.json', 'r', encoding='utf-8') as f:
    topics = json.load(f)

# Define the aggregation groups
groups = {
    "Family Days": [
        "Father's Day",
        "Mother's Day",
        "Parent's Day",
        "Grandparents' Day"
    ],
    "Western festivals": [
        "Thanksgiving",
        "Halloween",
        "Day of the Dead",
        "Valentines Day",
        "Pride Month",
        "St. David's Day",
        "St. Patrick's Day",
        "Black History Month",
        "Asian/Pacific American Heritage Month",
        "Hispanic Heritage Month",
        "Native American Heritage Month"
    ],
    "East Asian Festivals": [
        "Dragon Boat Festival",
        "Mid Autumn Festival",
        "Lantern Festival",
        "Qixi",
        "Tanabata",
        "Hinamatsuri",
        "Hangul Day",
        "Mountain Day",
        "Respect for the Aged Day",
        "Chuseok"
    ],
    "Google Doodle Events": [
        "Doodle For Google",
        "Google's Birthday",
        "New Google Logo"
    ],
    "New Year Celebrations": [
        "New Year's Day",
        "New Year's Eve",
        "Lunar New Year",
        "Nowruz"
    ],
    "World Cup Events": [
        "World Cup",
        "Women's World Cup"
    ],
    "Multi-sport Events": [
        "Olympics",
        "Paralympics",
        "Summer Games"
    ],
    "Remembrance Days": [
        "Memorial Day",
        "Veterans Day",
        "Juneteenth",
        "Indigenous People's Day",
        "Martin Luther King Jr. Day"
    ],
    "Children & Education": [
        "Children's Day",
        "First Day of School",
        "Teacher's Day",
        "Education"
    ],
    "Sports Events": [
        "American Football",
        "Cricket World Cup",
        "Archery",
        "Badmington",
        "Baseball",
        "Basketball",
        "Billiards",
        "Boules",
        "Bowling",
        "Cricket",
        "Cycling",
        "Equine",
        "Football/Soccer",
        "Golf",
        "Gymnastics",
        "Hockey",
        "Ice Skating",
        "Lacrosse",
        "Martial Arts",
        "Mountaineering",
        "Rock Climbing",
        "Rugby",
        "Skateboarding",
        "Skiing",
        "Stickball",
        "Surfing",
        "Swimming",
        "Table Tennis",
        "Tennis",
        "Track and Field",
        "Volleyball",
        "Water Sports",
        "Weight Lifting",
        "Winter Sports",
        "Wrestling",
        "Summer Games"
    ],
    "Games": [
        "Board Games",
        "Video Games"
    ],
    "Arts": [
        "Animation",
        "Architecture",
        "Ceramics",
        "Cinema",
        "Comedy",
        "Dance",
        "Design",
        "Fashion",
        "Glasswork",
        "Illustration",
        "Literature",
        "Music",
        "Painting",
        "Photography",
        "Poetry",
        "Printmaking",
        "Radio",
        "Sculpture",
        "Television/Film",
        "Textiles",
        "Theater",
        "Reoccuring Doodle Characters"
    ],
    "Natural World & Animals": [
        "Animals",
        "Fictional Animals",
        "Insects",
        "Plants & Flowers"
    ],
    "Geography & Landmarks": [
        "Man Made Landmarks",
        "Natural Landmarks"
    ],
    "Transportation & Aviation": [
        "Transportation",
        "Aviation"
    ],
    "Science & Technology": [
        "AI",
        "Archaeology",
        "Biology",
        "Cartography",
        "Chemistry",
        "Computer Science",
        "Earth Science",
        "Engineering",
        "Mathematics",
        "Ocean Science",
        "Physics",
        "Psychology",
        "Public Health",
        "Sociology / Anthropology",
        "Space",
        "Sustainability",
        "Telecommunications"
    ]
}

# Build the aggregated result
result = {}

# Add grouped topics
for group_name, topic_keys in groups.items():
    group_dict = {}
    for key in topic_keys:
        if key in topics:
            group_dict[key] = topics[key]
    if group_dict:  # Only add non-empty groups
        result[group_name] = group_dict

# Add ungrouped topics (those not in any group)
all_grouped_keys = set()
for topic_keys in groups.values():
    all_grouped_keys.update(topic_keys)

for key, value in topics.items():
    if key not in all_grouped_keys:
        result[key] = value

# Write the result to a new file
with open('topics_aggregated.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Aggregation complete. Saved to topics_aggregated.json")