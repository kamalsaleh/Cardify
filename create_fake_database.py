from app import app, db, Topic, Flashcard, Deck, DeckEntry, Image, Subtopic, FlashcardHierarchy
from faker import Faker
import random

app.app_context().push()
db.create_all()

fake = Faker()

topics = {
    "Mathematics": {
        "Algebra": ["Linear Algebra", "Abstract Algebra", "Boolean Algebra"],
        "Calculus": ["Differential Calculus", "Integral Calculus", "Multivariable Calculus"],
        "Geometry": ["Euclidean Geometry", "Non-Euclidean Geometry", "Differential Geometry"],
        "Number Theory": ["Prime Numbers", "Modular Arithmetic", "Cryptography"],
        "Probability and Statistics": ["Descriptive Statistics", "Inferential Statistics", "Bayesian Statistics"],
        "Discrete Mathematics": ["Graph Theory", "Combinatorics", "Logic"],
        "Mathematical Analysis": ["Real Analysis", "Complex Analysis", "Functional Analysis"],
        "Applied Mathematics": ["Numerical Methods", "Optimization", "Mathematical Modeling"]
    },
    "Physics": {
        "Classical Mechanics": ["Newtonian Mechanics", "Lagrangian Mechanics", "Hamiltonian Mechanics"],
        "Electromagnetism": ["Electric Fields", "Magnetic Fields", "Electromagnetic Waves"],
        "Thermodynamics": ["Laws of Thermodynamics", "Heat Transfer", "Statistical Mechanics"],
        "Quantum Mechanics": ["Wave-Particle Duality", "Quantum Field Theory", "Quantum Computing"],
        "Relativity": ["Special Relativity", "General Relativity", "Cosmology"],
        "Optics": ["Geometrical Optics", "Wave Optics", "Quantum Optics"],
        "Solid State Physics": ["Crystallography", "Semiconductor Physics", "Superconductivity"],
        "Particle Physics": ["Standard Model", "High-Energy Physics", "Particle Accelerators"]
    },
    "Chemistry": {
        "Organic Chemistry": ["Hydrocarbons", "Functional Groups", "Polymers"],
        "Inorganic Chemistry": ["Periodic Table", "Coordination Compounds", "Transition Metals"],
        "Physical Chemistry": ["Chemical Thermodynamics", "Kinetics", "Quantum Chemistry"],
        "Analytical Chemistry": ["Chromatography", "Spectroscopy", "Titrations"],
        "Biochemistry": ["Enzymes", "Metabolic Pathways", "Nucleic Acids"],
        "Environmental Chemistry": ["Air Pollution", "Water Chemistry", "Soil Chemistry"],
        "Industrial Chemistry": ["Petrochemicals", "Fertilizers", "Pharmaceuticals"]
    },
    "Biology": {
        "Cell Biology": ["Cell Structure", "Cell Cycle", "Organelles"],
        "Genetics": ["Mendelian Genetics", "Molecular Genetics", "Genetic Engineering"],
        "Evolution": ["Natural Selection", "Speciation", "Phylogenetics"],
        "Ecology": ["Ecosystems", "Biodiversity", "Conservation"],
        "Anatomy and Physiology": ["Human Anatomy", "Animal Physiology", "Plant Physiology"],
        "Microbiology": ["Bacteria", "Viruses", "Fungi"],
        "Biotechnology": ["CRISPR", "Cloning", "Biopharmaceuticals"]
    },
    "Computer": {
        "Programming": ["Languages (Python, Java, C++)", "Algorithms", "Data Structures"],
        "Computer Science": ["Theory of Computation", "Operating Systems", "Computer Architecture"],
        "Artificial Intelligence": ["Machine Learning", "Natural Language Processing", "Computer Vision"],
        "Software Development": ["Agile Methodologies", "Testing", "Version Control"],
        "Networking": ["TCP/IP", "Network Security", "Cloud Computing"],
        "Databases": ["SQL", "NoSQL", "Database Design"],
        "Cybersecurity": ["Encryption", "Ethical Hacking", "Cyber Laws"]
    },
    "Astronomy": {
        "Stellar Astronomy": ["Star Formation", "Stellar Evolution", "Supernovae"],
        "Planetary Science": ["Solar System", "Exoplanets", "Planetary Atmospheres"],
        "Cosmology": ["Big Bang Theory", "Dark Matter", "Dark Energy"],
        "Galactic Astronomy": ["Milky Way Galaxy", "Galactic Evolution", "Black Holes"],
        "Observational Astronomy": ["Telescopes", "Spectroscopy", "Space Missions"],
        "Astrobiology": ["Search for Extraterrestrial Life", "Extremophiles", "Habitable Zones"]
    },
    "History": {
        "Ancient History": ["Mesopotamia", "Ancient Egypt", "Greek and Roman Empires"],
        "Medieval History": ["Feudalism", "Crusades", "Byzantine Empire"],
        "Modern History": ["Industrial Revolution", "World Wars", "Decolonization"],
        "Cultural History": ["Art Movements", "Religions and Philosophies", "Social Movements"],
        "Political History": ["Revolutions", "Empires and Colonies", "International Relations"]
    },
    "Literature": {
        "Genres": ["Poetry", "Fiction", "Drama"],
        "Periods": ["Classical Literature", "Renaissance Literature", "Modernism and Postmodernism"],
        "World Literature": ["Asian Literature", "African Literature", "European Literature"],
        "Literary Criticism": ["Structuralism", "Post-Colonialism", "Feminism"],
        "Notable Authors": ["Shakespeare", "Tolstoy", "Chimamanda Ngozi Adichie"]
    },
    "Philosophy": {
        "Metaphysics": ["Ontology", "Free Will", "Dualism"],
        "Epistemology": ["Knowledge and Belief", "Rationalism vs Empiricism", "Skepticism"],
        "Ethics": ["Utilitarianism", "Deontology", "Virtue Ethics"],
        "Logic": ["Propositional Logic", "Predicate Logic", "Modal Logic"],
        "Philosophers": ["Socrates", "Kant", "Nietzsche"]
    },
    "Economics": {
        "Microeconomics": ["Supply and Demand", "Consumer Behavior", "Market Structures"],
        "Macroeconomics": ["GDP and Growth", "Inflation", "Fiscal and Monetary Policy"],
        "International Economics": ["Trade Theories", "Exchange Rates", "Globalization"],
        "Development Economics": ["Poverty", "Human Capital", "Sustainable Development"],
        "Econometrics": ["Regression Analysis", "Time Series", "Causal Inference"]
    },
    "Psychology": {
        "Cognitive Psychology": ["Memory", "Perception", "Problem-Solving"],
        "Developmental Psychology": ["Childhood Development", "Adolescence", "Aging"],
        "Clinical Psychology": ["Mental Disorders", "Psychotherapy", "Personality Disorders"],
        "Social Psychology": ["Group Dynamics", "Prejudice and Discrimination", "Social Influence"],
        "Neuropsychology": ["Brain Structure and Function", "Cognitive Neuroscience", "Brain Injuries"]
    },
    "Sociology": {
        "Social Institutions": ["Family", "Education", "Religion"],
        "Social Stratification": ["Class", "Gender", "Race and Ethnicity"],
        "Urban Sociology": ["Urbanization", "Gentrification", "Urban Planning"],
        "Globalization": ["Cultural Exchange", "Global Inequality", "Migration"],
        "Social Theories": ["Functionalism", "Conflict Theory", "Symbolic Interactionism"]
    },
    "Law": {
        "Constitutional Law": ["Fundamental Rights", "Judiciary", "Legislative Processes"],
        "Criminal Law": ["Crimes Against Persons", "White-Collar Crimes", "Cybercrime"],
        "Civil Law": ["Contracts", "Property Law", "Torts"],
        "International Law": ["Human Rights Law", "Trade Law", "Maritime Law"],
        "Corporate Law": ["Business Entities", "Mergers and Acquisitions", "Intellectual Property"]
    }
}

def create_tables(
      nr_deck_titles=40,
      max_nr_decks=900,
      nr_flashcards=3000,
      max_nr_deckentries=10000,
      nr_flashcard_hierarchies=12000
    ):
  
  Image.create_default_entry()
  Topic.create_default_entry()
  
  for topic_name in topics.keys():
    topic = Topic.query.filter_by(title=topic_name).first()
    if topic is None:
      topic = Topic(title=topic_name)
      db.session.add(topic)
  db.session.commit()
  
  for topic_name in topics.keys():
    for subtopic_name in topics[topic_name].keys():
      subtopic = Topic.query.filter_by(title=subtopic_name).first()
      if subtopic is None:
        subtopic = Topic(title=subtopic_name)
        db.session.add(subtopic)
    db.session.commit()
  
  for topic_name in topics.keys():
    topic = Topic.query.filter_by(title=topic_name).first()
    for subtopic_name in topics[topic_name].keys():
      subtopic = Topic.query.filter_by(title=subtopic_name).first()
      link = Subtopic(suptopic_id=topic.id, subtopic_id=subtopic.id)
      db.session.add(link)
  db.session.commit()
  
  for topic_name in topics.keys():
    for subtopic_name in topics[topic_name].keys():
      for subsubtopic_name in topics[topic_name][subtopic_name]:
        subsubtopic = Topic.query.filter_by(title=subsubtopic_name).first()
        if subsubtopic is None:
          subsubtopic = Topic(title=subsubtopic_name)
          db.session.add(subsubtopic)
      db.session.commit()
  
  for topic_name in topics.keys():
    for subtopic_name in topics[topic_name].keys():
      subtopic = Topic.query.filter_by(title=subtopic_name).first()
      for subsubtopic_name in topics[topic_name][subtopic_name]:
        subsubtopic = Topic.query.filter_by(title=subsubtopic_name).first()
        link = Subtopic(suptopic_id=subtopic.id, subtopic_id=subsubtopic.id)
        db.session.add(link)
  db.session.commit()
  
  nr_topics = Topic.query.count()
  
  deck_titles = [word.capitalize() + "-Deck" for word in fake.words(nb=nr_deck_titles, unique=True)]
  
  deck_infos = {(random.randint(1, nr_topics), random.choice(deck_titles)) for i in range(max_nr_decks)}
  
  for deck_info in deck_infos:
    deck = Deck(topic_id=deck_info[0], title=deck_info[1], description=fake.text(max_nb_chars=20))
    db.session.add(deck)
  db.session.commit()
  
  for i in range(nr_flashcards):
    title = fake.sentence(nb_words=random.randint(5, 10))
    content = fake.text(max_nb_chars=random.randint(50, 500))
    hint = fake.sentence(nb_words=random.randint(5, 10))
    notes = fake.text(max_nb_chars=random.randint(50, 500))
    flashcard = Flashcard(title=title, content=content, hint=hint, notes=notes)
    db.session.add(flashcard)
  db.session.commit()
  
  flashcards = Flashcard.query.all()
  decks = Deck.query.all()
  
  deckentry_infos = {(random.choice(decks).id, random.choice(flashcards).id) for i in range(max_nr_deckentries)}
  
  for deckentry_info in deckentry_infos:
    deckentry = DeckEntry(deck_id=deckentry_info[0], flashcard_id=deckentry_info[1])
    db.session.add(deckentry)
  db.session.commit()
  
  pairs = set()
  
  for _ in range(nr_flashcard_hierarchies):
    pre_card_id = random.randint(1, nr_flashcards-1)
    pos_card_id = random.randint(pre_card_id+1, nr_flashcards)
    pairs.add((pre_card_id, pos_card_id))
  
  for pre_card_id, pos_card_id in pairs:
    c = FlashcardHierarchy(pre_card_id=pre_card_id, pos_card_id=pos_card_id)
    db.session.add(c)
  db.session.commit()
  
  return 'Tables created'
