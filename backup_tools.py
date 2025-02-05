from app import app, db, Topic, Flashcard, Deck, DeckEntry, Image, Subtopic, FlashcardHierarchy
from pathlib import Path
import csv
import datetime

app.app_context().push()

def backup_table_to_csv(model, file_path):
  
  with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
      writer = csv.writer(csvfile)
      
      # Write header
      header = [column.name for column in model.__table__.columns]
      writer.writerow(header)
      
      # Fetch table data
      records = model.query.all()
      
      for record in records:
        writer.writerow([getattr(record, key) for key in header])
  
def backup_tables(time_stamp=None):
  
  if time_stamp is None:
    time_now = db.session.execute(db.select(db.func.now())).scalar()
    time_stamp = time_now.strftime('%Y-%m-%d_@_%H:%M:%S')
  
  try:
    backup_folder = Path(app.config['BACKUP_FOLDER']) / time_stamp
    backup_folder.mkdir(parents=True, exist_ok=True)
    
    backup_table_to_csv(Image, backup_folder / 'images.csv')
    backup_table_to_csv(Topic, backup_folder / 'topics.csv')
    backup_table_to_csv(Subtopic, backup_folder / 'subtopics.csv')
    backup_table_to_csv(Flashcard, backup_folder / 'flashcards.csv')
    backup_table_to_csv(Deck, backup_folder / 'decks.csv')
    backup_table_to_csv(DeckEntry, backup_folder / 'deck_entries.csv')
    backup_table_to_csv(FlashcardHierarchy, backup_folder / 'flashcard_hierarchy.csv')
    
    print(f'Backup successful at {backup_folder}')
  except Exception as e:
    print(f'Backup failed: {e}')
  
# read the data from the csv files to a db.session object
def load_tables_from_backup(time_stamp):
  
  # make sure the database is empty
  if db.session.query(Image).count() != 0:
    raise ValueError("Image table is not empty.")
  
  if db.session.query(Topic).count() != 0:
    raise ValueError("Topic table is not empty.")
  
  if db.session.query(Subtopic).count() != 0:
    raise ValueError("Subtopic table is not empty.")
  
  if db.session.query(Flashcard).count() != 0:
    raise ValueError("Flashcard table is not empty.")
  
  if db.session.query(Deck).count() != 0:
    raise ValueError("Deck table is not empty.")
  
  if db.session.query(DeckEntry).count() != 0:
    raise ValueError("DeckEntry table is not empty")
  
  if db.session.query(FlashcardHierarchy).count() != 0:
    raise ValueError("FlashcardHierarchy table is not empty.")
  
  backup_folder = Path(app.config['BACKUP_FOLDER']) / time_stamp
  
  if not backup_folder.exists():
    return f"Backup folder {backup_folder} does not exist."
  
  try:
    images = []
    topics = []
    subtopics = []
    flashcards = []
    decks = []
    deck_entries = []
    flashcard_hierarchy = []
    
    for file in backup_folder.iterdir():
      if file.suffix == '.csv':
        with open(file, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            
            for row in reader:
              data = dict(zip(header, row))
              
              if file.stem == 'images':
                data['add_date'] = datetime.datetime.strptime(data['add_date'], '%Y-%m-%d %H:%M:%S')
                images.append(Image(**data))
              elif file.stem == 'topics':
                data['add_date'] = datetime.datetime.strptime(data['add_date'], '%Y-%m-%d %H:%M:%S')
                topics.append(Topic(**data))
              elif file.stem == 'subtopics':
                subtopics.append(Subtopic(**data))
              elif file.stem == 'flashcards':
                data['flippable'] = True if data['flippable'] == 'True' else False
                data['add_date'] = datetime.datetime.strptime(data['add_date'], '%Y-%m-%d %H:%M:%S')
                data['last_modified_date'] = datetime.datetime.strptime(data['last_modified_date'], '%Y-%m-%d %H:%M:%S')
                flashcards.append(Flashcard(**data))
              elif file.stem == 'decks':
                decks.append(Deck(**data))
              elif file.stem == 'deck_entries':
                data['add_date'] = datetime.datetime.strptime(data['add_date'], '%Y-%m-%d %H:%M:%S')
                deck_entries.append(DeckEntry(**data))
              elif file.stem == 'flashcard_hierarchy':
                flashcard_hierarchy.append(FlashcardHierarchy(**data))
    
    db.session.bulk_save_objects(images)
    db.session.bulk_save_objects(topics)
    db.session.bulk_save_objects(subtopics)
    db.session.bulk_save_objects(flashcards)
    db.session.bulk_save_objects(decks)
    db.session.bulk_save_objects(deck_entries)
    db.session.bulk_save_objects(flashcard_hierarchy)
    
    db.session.commit()
    
    return f"Data loaded successfully from {backup_folder}"
  except Exception as e:
    return f"Data loading failed: {e}"

def delete_tables():
  user_input = input('Are you sure you want to delete all tables? (yes/no): ')
  if user_input.lower() in ['yes', 'y']:
    Subtopic.query.delete()
    FlashcardHierarchy.query.delete()
    DeckEntry.query.delete()
    Deck.query.delete()
    Topic.query.delete()
    Flashcard.query.delete()
    Image.query.delete()
    db.session.commit()
    return 'Tables deleted'
  else:
    return 'Tables not deleted'