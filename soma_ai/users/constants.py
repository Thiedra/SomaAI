"""
users/constants.py
Shared constants for the users app.
"""

RWANDAN_SCHOOLS = [
    "Riviera High School",
    "Gashora Girls Academy of Science and Technology",
    "Green Hills Academy",
    "FAWE Girls' School",
    "Lycée de Kigali",
    "Agahozo-Shalom Youth Village",
    "White Dove Global School",
    "Nu-Vision High School",
    "Wellspring Academy",
    "King David Academy",
    "ES Caf Muhese",
    "Groupe Scolaire Officiel de Butare",
    "Groupe Scolaire Sainte Bernadette de Save",
    "Collège du Christ-Roi",
    "Petit Séminaire Virgo Fidelis",
    "École des Sciences Byimana",
    "Stella Matutina",
    "Sonrise High School",
    "Hope Haven Rwanda",
    "Kigali International Community School",
]

SCHOOL_CHOICES = [(s, s) for s in RWANDAN_SCHOOLS]

GRADE_CHOICES = [
    ("P1", "Primary 1"),
    ("P2", "Primary 2"),
    ("P3", "Primary 3"),
    ("P4", "Primary 4"),
    ("P5", "Primary 5"),
    ("P6", "Primary 6"),
]

XP_PER_LEVEL = 2500  # frontend: level up at every 2500 XP
