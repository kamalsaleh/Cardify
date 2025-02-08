from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from forms import FlashcardForm, DeckForm, TopicForm, GenerateImageForm
from werkzeug.utils import secure_filename
import os
import shutil
from bs4 import BeautifulSoup
from pyvis.network import Network
from ai_tools import generate_image, generate_card
from keys import SECRET_KEY, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, DATABASE_NAME, BACKUP_FOLDER, IMAGES_FOLDER, GEN_IMAGES_FOLDER, GRAPH_FILE
import mysql.connector

app = Flask(__name__)

# Set up the secret key
app.config['SECRET_KEY'] = SECRET_KEY

# Step 1: Connect to MySQL and create the database if it doesn’t exist
def create_database():
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}")
    cursor.close()
    connection.close()

create_database()

# Set up the MYSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{DATABASE_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set up the upload folder
app.config['BACKUP_FOLDER'] = BACKUP_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['GEN_IMAGES_FOLDER'] = GEN_IMAGES_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['DARK_THEME'] = True

# Set up the number of items per page
app.config['PER_PAGE'] = 5

# Declare the database
db = SQLAlchemy(app)

# Set up the migration engine
migrate = Migrate(app, db)

class Topic(db.Model):
  __tablename__ = 'topic_table'
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(50), nullable=False, unique=True)
  add_date = db.Column(db.DateTime, default=db.func.now())

  def title_text(self, N=10**3):
    title = self.title
    return title[0:N] + ' ...' if len(title) > N else title

  def suptopics(self):
    return list({suptopic_ref.suptopic for suptopic_ref in self.suptopic_references})

  def suptopic_ids(self):
    return [suptopic.id for suptopic in self.suptopics()]

  def all_suptopics(self):
    suptopics = self.suptopics()
    for suptopic in suptopics:
      suptopics.extend(suptopic.all_suptopics())
    return list(set(suptopics))

  def all_suptopic_ids(self):
    return [suptopic.id for suptopic in self.all_suptopics()]

  def subtopics(self):
    return list({subtopic_ref.subtopic for subtopic_ref in self.subtopic_references})

  def subtopic_ids(self):
    return [subtopic.id for subtopic in self.subtopics()]

  def all_subtopics(self):
    subtopics = self.subtopics()
    for subtopic in subtopics:
      subtopics.extend(subtopic.all_subtopics())
    return list(set(subtopics))

  def all_subtopic_ids(self):
    return [subtopic.id for subtopic in self.all_subtopics()]

  def deck_ids(self):
    return [deck.id for deck in self.decks]

  def deck_titles(self):
    return [deck.title for deck in self.decks]

  def flashcards(self):
    return list(set(sum([deck.flashcards() for deck in self.decks], [])))

  def flashcard_ids(self):
    return list(set(sum([deck.flashcard_ids() for deck in self.decks], [])))

  def create_default_entry(db=db):
    if Topic.query.count() == 0:
      topic = Topic(title='Default topic')
      db.session.add(topic)
      db.session.commit()

  def __repr__(self):
    return f'<Topic: id={self.id}, title={self.title!r}>'

class Subtopic(db.Model):
  __tablename__ = 'subtopic_table'
  suptopic_id = db.Column(db.Integer, db.ForeignKey('topic_table.id', ondelete='CASCADE'), primary_key=True)
  subtopic_id = db.Column(db.Integer, db.ForeignKey('topic_table.id', ondelete='CASCADE'), primary_key=True)

  # How beutiful is this? :)
  suptopic = db.relationship('Topic', foreign_keys=[suptopic_id], backref='subtopic_references')
  subtopic = db.relationship('Topic', foreign_keys=[subtopic_id], backref='suptopic_references')

  __table_args__ = (
      db.PrimaryKeyConstraint('suptopic_id', 'subtopic_id'),
  )

  def __repr__(self):
      return f'<Subtopic: suptopic_id={self.suptopic_id}, subtopic_id={self.subtopic_id}; Details: suptopic.title={self.suptopic.title!r}, subtopic.title={self.subtopic.title!r}>'

class Deck(db.Model):
  __tablename__ = 'deck_table'
  id = db.Column(db.Integer, primary_key=True)
  topic_id = db.Column(db.Integer, db.ForeignKey('topic_table.id', ondelete='SET NULL'), default=1)
  title = db.Column(db.String(100), nullable=False)
  description = db.Column(db.Text, default='')

  __table_args__ = (db.UniqueConstraint('topic_id', 'title', name='unique_topic_title'),)

  topic = db.relationship('Topic', backref=db.backref('decks', lazy=True))

  def title_text(self, N=10**3):
    title = self.title
    return title[0:N] + ' ...' if len(title) > N else title

  def total(self):
    return len(self.deckentries)

  def flashcards(self):
    return [deckentry.flashcard for deckentry in self.deckentries]

  def flashcard_ids(self):
    return [flashcard.id for flashcard in self.flashcards()]

  def __repr__(self):
    return f'<Deck: id={self.id}, topic={self.topic.title}, title={self.title!r}>'

class Image(db.Model):
  __tablename__ = 'image_table'
  id = db.Column(db.Integer, primary_key=True)
  filename = db.Column(db.String(255), nullable=False, unique=True)
  description = db.Column(db.Text, default='')
  add_date = db.Column(db.DateTime, default=db.func.now())

  def flashcard_ids(self):
    return [flashcard.id for flashcard in self.flashcards]

  def __repr__(self):
    return f'<Image: id={self.id}, filename={self.filename!r}>'

  def create_default_entry(db=db):
    if Image.query.count() == 0:
      filename=''.join(['0' for i in range(36)]) + '-' + ''.join(['0' for i in range(32)]) + '.png'
      image = Image(filename=filename, description='Default image')
      db.session.add(image)
      db.session.commit()

class Flashcard(db.Model):
  __tablename__ = 'flashcard_table'
  id = db.Column(db.Integer, primary_key=True)
  flippable = db.Column(db.Boolean, default=False)
  title = db.Column(db.Text, nullable=False)
  content = db.Column(db.Text, nullable=False)
  hint = db.Column(db.Text, default='')
  notes = db.Column(db.Text, default='')
  add_date = db.Column(db.DateTime, default=db.func.now())
  last_modified_date = db.Column(db.DateTime, default=db.func.now())
  image_id = db.Column(db.Integer, db.ForeignKey('image_table.id', ondelete='SET NULL'), nullable=True, default=1)

  # The image object that is linked to this flashcard
  image = db.relationship('Image', backref=db.backref('flashcards', lazy=True))

  def title_text(self, N=10**3):
    title = self.title
    return title[0:N] + ' ...' if len(title) > N else title

  def content_text(self, N=10**3):
    content = BeautifulSoup(self.content, 'html.parser').get_text()
    return content[0:N] + ' ...' if len(content) > N else content

  def hint_text(self, N=10**3):
    hint = self.hint
    return hint[0:N] + ' ...' if len(hint) > N else hint

  def notes_text(self, N=10**3):
    notes = BeautifulSoup(self.notes, 'html.parser').get_text()
    return notes[0:N] + ' ...' if len(notes) > N else notes

  # Thanks sqlalchemy for the backref feature :)
  def decks(self):
    return [deckentry.deck for deckentry in self.deckentries]

  def deck_titles(self):
    return [deck.title for deck in self.decks()]

  def deck_ids(self):
    return [deck.id for deck in self.decks()]

  def topics(self):
    return list({deck.topic for deck in self.decks()})

  def topictitles(self):
    return [topic.title for topic in self.topics()]

  def topicids(self):
    return [topic.id for topic in self.topics()]

  # The hierarchy of flashcards
  def pre_cards(self):
    return list({pre_card_ref.pre_card for pre_card_ref in self.pre_card_references})

  def pre_card_ids(self):
    return [pre_card.id for pre_card in self.pre_cards()]

  def pos_cards(self):
    return list({pos_card_ref.pos_card for pos_card_ref in self.pos_card_references})

  def pos_card_ids(self):
    return [pos_card.id for pos_card in self.pos_cards()]

  # "all_" methods are recursive and very expensive
  def all_pre_cards(self):
    pre_cards = self.pre_cards()
    for pre_card in pre_cards:
      pre_cards.extend(pre_card.all_pre_cards())
    return list(set(pre_cards))

  def all_pre_card_ids(self):
    return [pre_card.id for pre_card in self.all_pre_cards()]

  def all_pos_cards(self):
    pos_cards = self.pos_cards()
    for pos_card in pos_cards:
      pos_cards.extend(pos_card.all_pos_cards())
    return list(set(pos_cards))

  def all_pos_card_ids(self):
    return [pos_card.id for pos_card in self.all_pos_cards()]

  def __repr__(self):
    return f'<Flashcard: id={self.id}, title={self.title_text()}>'

class FlashcardHierarchy(db.Model):
  __tablename__ = 'flashcardhierarchy_table'
  pre_card_id = db.Column(db.Integer, db.ForeignKey('flashcard_table.id', ondelete='CASCADE'), primary_key=True)
  pos_card_id = db.Column(db.Integer, db.ForeignKey('flashcard_table.id', ondelete='CASCADE'), primary_key=True)

  pre_card = db.relationship('Flashcard', foreign_keys=[pre_card_id], backref='pos_card_references')
  pos_card = db.relationship('Flashcard', foreign_keys=[pos_card_id], backref='pre_card_references')

  __table_args__ = (
      db.PrimaryKeyConstraint('pre_card_id', 'pos_card_id'),
  )

  def __repr__(self):
      return f'<FlashcardHierarchy: pre_card_id={self.pre_card_id}, pos_card_id={self.pos_card_id}; Details: pre_card.title={self.pre_card.title_text()!r}, pos_card.title={self.pos_card.title_text()!r}>'

class DeckEntry(db.Model):
  __tablename__ = 'deckentry_table'

  # Link to the Deck table using the 'deck_id' column to the 'id' column in the Deck table
  # Each deck entry can only have one deck, but a deck can have multiple deck entries, i.e., it is a one-to-many relationship
  deck_id = db.Column(db.Integer, db.ForeignKey('deck_table.id', ondelete='CASCADE'), nullable=False)

  # Link to the Flashcard table using the 'flashcard_id' column to the 'id' column in the Flashcard table
  # Each deck entry can only have one flashcard, but a flashcard can be in multiple decks, i.e., it is a many-to-one relationship
  flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcard_table.id', ondelete='CASCADE'), nullable=False)

  # The flashcard object that is linked to this deck entry
  flashcard = db.relationship('Flashcard', backref=db.backref('deckentries', lazy=True))

  # The deck object that is linked to this deck entry
  deck = db.relationship('Deck', backref=db.backref('deckentries', lazy=True))

  add_date = db.Column(db.DateTime, default=db.func.now())

  __table_args__ = (
      db.PrimaryKeyConstraint('flashcard_id', 'deck_id'),
  )

  def __repr__(self):
      return f'<DeckEntry: flashcard_id={self.flashcard_id}, title={self.deck_id!r}>'

@app.route('/')
def home():
  return render_template('home.html')

@app.route('/view-topic/<int:id>', methods=['GET'])
def view_topic(id):
  topic = Topic.query.get_or_404(id)

  sup_and_sub_topics =  topic.all_suptopics() + topic.all_subtopics()
  topics = Topic.query.filter(Topic.id != id).order_by(db.func.lower(Topic.title))

  fiesible_suptopics = set(topics).difference(sup_and_sub_topics)
  suptopics = topic.suptopics()

  return render_template('view-topic.html',
            topic=topic,
            fiesible_suptopics=fiesible_suptopics,
            suptopics=suptopics,
          )

@app.route('/add-topic', methods=['GET', 'POST'])
def add_topic():
  form = TopicForm()

  if form.validate_on_submit():

    try:
      topic = Topic.query.filter_by(title=form.TITLE.data).first()
      if topic:
        flash('Topic already exists!', 'warning')
        return redirect(url_for('view_topic', id=topic.id))
      else:
        title = form.TITLE.data
        topic = Topic(title=title)
        db.session.add(topic)
        db.session.commit()
        flash('Topic added successfully!', 'success')
        return redirect(url_for('view_topic', id=topic.id))
    except Exception as e:
      db.session.rollback()
      flash(str(e), 'danger')

  return render_template('edit-topic.html', form=form, header="New Topic")

@app.route('/edit-topic/<int:id>', methods=['GET', 'POST'])
def edit_topic(id):
  topic = Topic.query.filter_by(id=id).first()

  form = TopicForm(TITLE=topic.title)

  if form.validate_on_submit():

    try:
      if topic.title != form.TITLE.data:
        topic.title = form.TITLE.data
        topic.last_modified_date = db.func.now()
        db.session.commit()

        flash('Topic updated successfully!', 'success')
      else:
        flash('No changes were made.', 'info')
    except Exception as e:
      db.session.rollback()
      flash(str(e), 'danger')

    return redirect(url_for('view_topic', id=topic.id))

  return render_template('edit-topic.html', form=form, header = f"Edit Topic: &#x201C;{ topic.id }&#x201D;")

@app.route('/add-subtopic/<int:suptopic_id>/<int:subtopic_id>', methods=['POST'])
def add_subtopic(suptopic_id, subtopic_id):
  try:
    subtopic_ref = Subtopic(suptopic_id=suptopic_id, subtopic_id=subtopic_id)
    db.session.add(subtopic_ref)
    db.session.commit()
    flash('Parent topic added successfully!', 'success')
  except Exception as e:
    db.session.rollback()
    flash(str(e), 'danger')

  return redirect(url_for('view_topic', id=subtopic_id))

@app.route('/delete-subtopic/<int:suptopic_id>/<int:subtopic_id>', methods=['POST', 'DELETE'])
def delete_subtopic(suptopic_id, subtopic_id):
  try:
    subtopic_ref = Subtopic.query.filter_by(suptopic_id=suptopic_id, subtopic_id=subtopic_id).first()
    db.session.delete(subtopic_ref)
    db.session.commit()
    flash('Parent topic deleted successfully!', 'success')
  except Exception as e:
    db.session.rollback()
    flash(str(e), 'danger')

  return redirect(url_for('view_topic', id=subtopic_id))

@app.route('/delete-topic/<int:id>', methods=['POST', 'DELETE'])
def delete_topic(id):
  topic = Topic.query.get_or_404(id)

  try:
    for suptopic_ref in topic.suptopic_references:
      db.session.delete(suptopic_ref)

    for subtopic_ref in topic.subtopic_references:
      db.session.delete(subtopic_ref)

    for deck in topic.decks:
      for deckentry in deck.deckentries:
        db.session.delete(deckentry)
      db.session.delete(deck)

    db.session.commit()

    db.session.delete(topic)
    db.session.commit()

    flash('Topic deleted successfully!', 'success')
  except Exception as e:
    db.session.rollback()
    flash(str(e), 'danger')

  return redirect(url_for('browse_topics'))

@app.route('/topic-graph/<int:id>')
def topic_graph(id):

    # For colors
    # https://htmlcolorcodes.com/

    # Create a Pyvis network

    if app.config['DARK_THEME']:
      net = Network(width="100%", height="800px", bgcolor="#222222", font_color="white")
    else:
      net = Network(width="100%", height="800px")

    topic = Topic.query.get_or_404(id)

    # node for topic
    net.add_node(
      f"topic-{topic.id}",
      label=topic.title,
      size=40,
      title=f"Decks: {len(topic.decks)}, Cards: {len(topic.flashcards())}",
      shape='image',
      image="/static/icons/topic.png",
      url = "/view-topic/" + str(topic.id)
    )

    # add and connect all direct sup-topics
    for suptopic in topic.suptopics():
        net.add_node(
          f"topic-{suptopic.id}",
          label=suptopic.title,
          size=30,
          title=f"Decks: {len(suptopic.decks)}, Cards: {len(suptopic.flashcards())}",
          shape='image',
          image="/static/icons/topic.png",
          url="/topic-graph/" + str(suptopic.id)
        )

        net.add_edge(
          f"topic-{suptopic.id}",
          f"topic-{topic.id}",
          arrowStrikethrough=False,
          arrows='to',
          physics=True
        )

    # add and connect all direct subtopics
    for subtopic in topic.subtopics():
        net.add_node(
          f"topic-{subtopic.id}",
          label=subtopic.title,
          size=30,
          title=f"Decks: {len(subtopic.decks)}, Cards: {len(subtopic.flashcards())}",
          shape='image',
          image="/static/icons/topic.png",
          url="/topic-graph/" + str(subtopic.id)
        )

        net.add_edge(
          f"topic-{topic.id}",
          f"topic-{subtopic.id}",
          arrowStrikethrough=False,
          arrows='to',
          physics=True
        )

    # nodes for decks
    for deck in topic.decks:
        net.add_node(
          f"deck-{deck.id}",
          label=deck.title,
          size=20,
          title=f"Cards: {len(deck.flashcards())}",
          shape='image',
          image="/static/icons/deck.png",
          url="/deck-graph/" + str(deck.id)
        )

        net.add_edge(
          f"topic-{topic.id}",
          f"deck-{deck.id}",
          physics=True
          )

    # use algorithms to position the nodes: barnes_hut, force_atlas_2based, repulsion
    # net.show_buttons(filter_=['physics'])
    net.force_atlas_2based()

    html_content = net.generate_html()

    custom_js = """
    <script>
      // Add click event listener to nodes
      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          // Get the node ID
          const nodeId = params.nodes[0];
          // Get the node data
          const nodeData = nodes.get(nodeId);

          // Check if a URL exists
          if (nodeData.url) {
            // Redirect to the URL (open in the same tab)
            window.location.href = nodeData.url;
          }
        }
      });
    </script>
    """
    
    html_content = html_content.replace("</body>", custom_js + "</body>")
    
    return render_template("graph.html", html_content=html_content)

@app.route('/deck-graph/<int:id>')
def deck_graph(id):

    # For colors
    # https://htmlcolorcodes.com/

    if app.config['DARK_THEME']:
      net = Network(width="100%", height="800px", bgcolor="#222222", font_color="white")
    else:
      net = Network(width="100%", height="800px")

    deck = Deck.query.get_or_404(id)

    # add the topic node
    net.add_node(
      f"topic-{deck.topic.id}",
      label=deck.topic.title,
      size=25,
      title=f"Decks: {len(deck.topic.decks)}, Cards: {len(deck.topic.flashcards())}",
      shape='image',
      image="/static/icons/topic.png",
      url="/topic-graph/" + str(deck.topic.id)
    )

    # add the deck node
    net.add_node(
      f"deck-{deck.id}",
      label=deck.title,
      size=30,
      title=f"Cards: {len(deck.flashcards())}",
      shape='image',
      image="/static/icons/deck.png",
      url="/view-deck/" + str(deck.id)
    )

    # add edge from topic to deck
    net.add_edge(
      f"topic-{deck.topic.id}",
      f"deck-{deck.id}",
      physics=True
    )

    deck_flashcards = set(deck.flashcards())

    for flashcard in deck_flashcards:
      title_text = flashcard.title_text()
      net.add_node(flashcard.id,
        label= title_text[0:20] + ' ...' if len(title_text) > 20 else title_text,
        size=20,
        title=title_text,
        shape='image',
        image="/static/icons/flash-card.png",
        url="/view-card/" + str(flashcard.id)
      )

    main_flashcards = [flashcard for flashcard in deck_flashcards if not deck_flashcards.intersection(flashcard.pre_cards())]

    for flashcard in main_flashcards:

      net.add_edge(
        f"deck-{deck.id}",
        flashcard.id,
        physics=True
      )

    for flashcard_1 in deck_flashcards:
      for flashcard_2 in deck_flashcards.intersection(flashcard_1.pos_cards()):

        net.add_edge(
          flashcard_1.id,
          flashcard_2.id,
          arrowStrikethrough=False,
          arrows='to',
          physics=True
        )

    # use algorithms to position the nodes: barnes_hut, force_atlas_2based, repulsion
    net.force_atlas_2based()
    #net.show_buttons(filter_=['physics'])

    html_content = net.generate_html()
    
    custom_js = """
    <script>
      // Add click event listener to nodes
      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          // Get the node ID
          const nodeId = params.nodes[0];
          // Get the node data
          const nodeData = nodes.get(nodeId);

          // Check if a URL exists
          if (nodeData.url) {
            // Redirect to the URL (open in the same tab)
            window.location.href = nodeData.url;
          }
        }
      });
    </script>
    """
    
    html_content = html_content.replace("</body>", custom_js + "</body>")
    
    return render_template("graph.html", html_content=html_content)

@app.route('/poscards-graph/<int:id>')
def poscards_graph(id):

    # For colors
    # https://htmlcolorcodes.com/

    if app.config['DARK_THEME']:
      net = Network(width="100%", height="800px", bgcolor="#222222", font_color="white")
    else:
      net = Network(width="100%", height="800px")

    flashcard = Flashcard.query.get_or_404(id)

    # add the flashcard node
    title_text = flashcard.title_text()
    net.add_node(
      f"flashcard-{flashcard.id}",
      label=title_text[0:20] + ' ...' if len(title_text) > 20 else title_text,
      size=30,
      title=title_text,
      shape='image',
      image="/static/icons/flash-card.png",
      url="/view-card/" + str(flashcard.id)
    )

    # add the deck nodes
    for deck in flashcard.decks():
      net.add_node(
        f"deck-{deck.id}",
        label=deck.title,
        size=30,
        title=f"Cards: {len(deck.flashcards())}",
        shape='image',
        image="/static/icons/deck.png",
        url="/deck-graph/" + str(deck.id),
      )

      net.add_edge(
        f"deck-{deck.id}",
        f"flashcard-{flashcard.id}",
        physics=True
      )

    # add the pos-cards
    for pos_card in flashcard.pos_cards():
        title_text = pos_card.title_text()
        net.add_node(
          f"flashcard-{pos_card.id}",
          label=title_text[0:20] + ' ...' if len(title_text) > 20 else title_text,
          size=20,
          title=title_text,
          shape='image',
          image="/static/icons/flash-card.png",
          url="/poscards-graph/" + str(pos_card.id)
        )

        net.add_edge(
          f"flashcard-{flashcard.id}",
          f"flashcard-{pos_card.id}",
          arrowStrikethrough=False,
          arrows='to',
          physics=True
        )

    # use algorithms to position the nodes: barnes_hut, force_atlas_2based, repulsion
    net.force_atlas_2based()
    #net.show_buttons(filter_=['physics'])

    html_content = net.generate_html()

    custom_js = """
    <script>
      // Add click event listener to nodes
      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          // Get the node ID
          const nodeId = params.nodes[0];
          // Get the node data
          const nodeData = nodes.get(nodeId);

          // Check if a URL exists
          if (nodeData.url) {
            // Redirect to the URL (open in the same tab)
            window.location.href = nodeData.url;
          }
        }
      });
    </script>
    """
    
    html_content = html_content.replace("</body>", custom_js + "</body>")
    
    return render_template("graph.html", html_content=html_content)

@app.route('/precards-graph/<int:id>')
def precards_graph(id):

    # For colors
    # https://htmlcolorcodes.com/

    if app.config['DARK_THEME']:
      net = Network(width="100%", height="800px", bgcolor="#222222", font_color="white")
    else:
      net = Network(width="100%", height="800px")

    flashcard = Flashcard.query.get_or_404(id)

    # add the flashcard node
    title_text = flashcard.title_text()
    net.add_node(
      f"flashcard-{flashcard.id}",
      label=title_text[0:20] + ' ...' if len(title_text) > 20 else title_text,
      size=30,
      title=title_text,
      shape='image',
      image="/static/icons/flash-card.png",
      url="/view-card/" + str(flashcard.id)
    )

    # add the deck nodes
    for deck in flashcard.decks():
      net.add_node(
        f"deck-{deck.id}",
        label=deck.title,
        size=30,
        title=f"Cards: {len(deck.flashcards())}",
        shape='image',
        image="/static/icons/deck.png",
        url="/deck-graph/" + str(deck.id),
      )

      net.add_edge(
        f"deck-{deck.id}",
        f"flashcard-{flashcard.id}",
        physics=True
      )

    # add the pre-cards
    for pre_card in flashcard.pre_cards():
        title_text = pre_card.title_text()
        net.add_node(
          f"flashcard-{pre_card.id}",
          label=title_text[0:20] + ' ...' if len(title_text) > 20 else title_text,
          size=20,
          title=title_text,
          shape='image',
          image="/static/icons/flash-card.png",
          url="/precards-graph/" + str(pre_card.id)
        )

        net.add_edge(
          f"flashcard-{pre_card.id}",
          f"flashcard-{flashcard.id}",
          arrowStrikethrough=False,
          arrows='to',
          physics=True
        )

    # use algorithms to position the nodes: barnes_hut, force_atlas_2based, repulsion
    net.force_atlas_2based()
    # net.show_buttons(filter_=['physics'])

    html_content = net.generate_html()

    custom_js = """
    <script>
      // Add click event listener to nodes
      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          // Get the node ID
          const nodeId = params.nodes[0];
          // Get the node data
          const nodeData = nodes.get(nodeId);

          // Check if a URL exists
          if (nodeData.url) {
            // Redirect to the URL (open in the same tab)
            window.location.href = nodeData.url;
          }
        }
      });
    </script>
    """
    
    html_content = html_content.replace("</body>", custom_js + "</body>")
    
    return render_template("graph.html", html_content=html_content)

@app.route('/add-card', methods=['GET', 'POST'])
def add_card():
  form = FlashcardForm()

  if form.validate_on_submit():

    toggle_generate = request.form.get('TOGGLE_GENERATE', type=int)

    if toggle_generate:

      response = generate_card(
                    content_prompt= request.form.get('CONTENT_PROMPT'),
                    hint_prompt= request.form.get('HINT_PROMPT'),
                    notes_prompt=request.form.get('NOTES_PROMPT')
      )

      flippable=True
      title = form.TITLE.data
      content = response['content']
      hint = response['hint']
      notes = response['notes']
      image_id = 1

    else:
      flippable=True
      title=form.TITLE.data
      content=form.CONTENT.data
      hint=form.HINT.data
      notes=form.NOTES.data

      image = form.IMAGE.data

      if image:
        image_filename = secure_filename(image.filename)
        image_entry = Image.query.filter_by(filename=image_filename).first()
        if not image_entry:
          image.save(os.path.join(app.config['IMAGES_FOLDER'], image_filename))
          image_entry = Image(filename=image_filename, description='Manual upload')
          db.session.add(image_entry)
          db.session.commit()
        image_id = image_entry.id
      else:
        image_id = 1

    try:
      flashcard = Flashcard(
        flippable=flippable,
        title=title,
        content=content,
        hint=hint,
        notes=notes,
        image_id=image_id
      )

      db.session.add(flashcard)
      db.session.commit()

      flash('Flashcard added successfully!', 'success')
      return redirect(url_for('view_card', id=flashcard.id))
    except Exception as e:
      flash(str(e), 'danger')
      db.session.rollback()

  return render_template('add-card-quill.html', form=form, header="New Flashcard")

def update_card_image(flashcard, image_filename, image_description):
  try:
    image = Image.query.filter_by(filename=image_filename).first()
    if not image:
      image = Image(filename=image_filename, description=image_description)
      db.session.add(image)
      db.session.commit()

    flashcard.image_id = image.id
    flashcard.last_modified_date = db.func.now()
    db.session.commit()

  except Exception as e:
    flash(str(e), 'danger')
    db.session.rollback()

@app.route('/generate-card-image/<int:id>', methods=['GET', 'POST'])
def generate_card_image(id):

  flashcard = Flashcard.query.get_or_404(id)

  form = GenerateImageForm()

  if form.validate_on_submit():

    try:
      card_as_context = request.form.get('CARD_AS_CONTEXT', type=bool)
      description_prompt = request.form.get('PROMPT')

      if card_as_context:
        image_filename = generate_image(prompts_dict={
            'title_prompt': flashcard.title_text(),
            'content_prompt': flashcard.content_text(),
            'hint_prompt': flashcard.hint_text() ,
            'notes_prompt': flashcard.notes_text(),
            'description_prompt': description_prompt
          },
          images_dir=app.config['GEN_IMAGES_FOLDER'],
          response_format="b64_json"
        )
      else:
        image_filename = generate_image(prompts_dict={
            'description_prompt': description_prompt
          },
          images_dir=app.config['GEN_IMAGES_FOLDER'],
          response_format="b64_json"
        )

      shutil.copy(os.path.join(app.config["GEN_IMAGES_FOLDER"], image_filename), os.path.join(app.config["IMAGES_FOLDER"], image_filename))

      update_card_image(flashcard, image_filename, description_prompt)

      return redirect(url_for('view_card', id=flashcard.id))
    except Exception as e:
      flash(str(e), 'danger')
      db.session.rollback()

  return render_template('generate-card-image.html', form=form, flashcard=flashcard)

@app.route('/edit-card/<int:id>', methods=['GET', 'POST'])
def edit_card(id):
  flashcard = Flashcard.query.get_or_404(id)
  form = FlashcardForm(
    FLIPPABLE=flashcard.flippable,
    TITLE=flashcard.title,
    CONTENT=flashcard.content,
    HINT=flashcard.hint,
    NOTES=flashcard.notes,
  )

  if form.validate_on_submit():

    prompt = request.form.get('IMAGE_PROMPT', '')

    try:
      flashcard.flippable = form.FLIPPABLE.data
      flashcard.title = form.TITLE.data
      flashcard.content = form.CONTENT.data
      flashcard.hint = form.HINT.data
      flashcard.notes = form.NOTES.data
      flashcard.last_modified_date = db.func.now()

      image = form.IMAGE.data

      if image:

        image_filename = secure_filename(image.filename)
        image_entry = Image.query.filter_by(filename=image_filename).first()
        if not image_entry:
          image.save(os.path.join(app.config['IMAGES_FOLDER'], image_filename))

        update_card_image(flashcard, image_filename, "Manual upload")
      else:
        db.session.commit()

      flash('Card updated successfully!', 'success')
    except Exception as e:
      flash(str(e), 'danger')
      db.session.rollback()

    return redirect(url_for('view_card', id=flashcard.id))

  return render_template('add-card-quill.html', form=form, header=f"Edit Flashcard: &#x201C;{ flashcard.id }&#x201D;")

@app.route('/delete-card/<int:id>', methods=['POST', 'DELETE'])
def delete_card(id):
  flashcard = Flashcard.query.get_or_404(id)

  try:

    for deckentry in flashcard.deckentries:
      db.session.delete(deckentry)

    db.session.commit()

    for pre_card_ref in flashcard.pre_card_references:
      db.session.delete(pre_card_ref)

    for pos_card_ref in flashcard.pos_card_references:
      db.session.delete(pos_card_ref)

    db.session.commit()

    db.session.delete(flashcard)
    db.session.commit()

    flash('Card deleted successfully!', 'success')
  except Exception as e:
    flash(str(e), 'danger')
    db.session.rollback()
    return redirect(url_for('view_card', id=flashcard.id))

  return redirect(url_for('home'))

@app.route('/view-card/<int:id>')
def view_card(id):
  card = Flashcard.query.get_or_404(id)
  card_deck_ids = card.deck_ids()
  decks = Deck.query.filter(Deck.id.notin_(card_deck_ids)).order_by(db.func.lower(Deck.title)).all()

  cards = Flashcard.query.filter(Flashcard.id != id).all()
  card_ids = set([card.id for card in cards])

  pre_cards = card.pre_cards()

  return render_template('view-card.html',
            flashcard=card,
            decks=decks,
            card_ids=card_ids,
            current_pre_cards=pre_cards,
  )

@app.route('/add-hierarchy/<int:pre_card_id>/<int:pos_card_id>', methods=['POST'])
def add_hierarchy(pre_card_id, pos_card_id):
  try:
    hierarchy = FlashcardHierarchy(pre_card_id=pre_card_id, pos_card_id=pos_card_id)
    db.session.add(hierarchy)
    db.session.commit()
    flash('A flashcard hierarchy added successfully!', 'success')
  except Exception as e:
    db.session.rollback()
    flash(str(e), 'danger')

  return redirect(url_for('view_card', id=pos_card_id))

@app.route('/delete-hierarchy/<int:pre_card_id>/<int:pos_card_id>', methods=['POST', 'DELETE'])
def delete_hierarchy(pre_card_id, pos_card_id):
  try:
    hierarchy = FlashcardHierarchy.query.filter_by(pre_card_id=pre_card_id, pos_card_id=pos_card_id).first()
    db.session.delete(hierarchy)
    db.session.commit()
    flash('A flashcard hierarchy deleted successfully!', 'success')
  except Exception as e:
    db.session.rollback()
    flash(str(e), 'danger')

  return redirect(url_for('view_card', id=pos_card_id))

@app.route('/browse-cards', methods=['GET', 'POST'])
def browse_cards():

  if request.method == 'POST':
    search_term = request.form.get('search_term', '')
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', app.config['PER_PAGE'], type=int)
    deck_id = request.form.get('deck_id', 0)
    decks = request.form.get('decks', '')
    search_logic = request.form.get('search_logic', '')
  else:
    search_term = request.args.get('search_term', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', app.config['PER_PAGE'], type=int)
    deck_id = request.args.get('deck_id', 0)
    decks = request.args.get('decks', '')
    search_logic = request.args.get('search_logic', '')

  decks_info = [info for info in decks.split('|') if info]
  alldecks = Deck.query.order_by(db.func.lower(Deck.title)).all()
  deck_ids = [deck.id for deck in alldecks if (deck.title + " / " + deck.topic.title) in decks_info]

  if deck_ids:
    if search_logic == 'any':
      flashcards = Flashcard.query.join(DeckEntry).filter(DeckEntry.deck_id.in_(deck_ids)).distinct()
    elif search_logic == 'all':
      flashcards = Flashcard.query.join(DeckEntry).filter(DeckEntry.deck_id.in_(deck_ids)).group_by(Flashcard.id).having(db.func.count(Flashcard.id) == len(deck_ids))
  else:
    flashcards = Flashcard.query

  if search_term:
    flashcards = flashcards.filter(
        Flashcard.title.ilike(f"%{search_term}%") |
        Flashcard.content.ilike(f"%{search_term}%") |
        Flashcard.hint.ilike(f"%{search_term}%") |
        Flashcard.notes.ilike(f"%{search_term}%")
      )

  # sort by add_date
  flashcards = flashcards.order_by(Flashcard.add_date.desc())

  # Pagination
  flashcards = flashcards.paginate(page=page, per_page=per_page, error_out=False)

  deck = Deck.query.get(deck_id) if deck_id else None

  alldecks = [deck.title + " / " + deck.topic.title for deck in alldecks]

  return render_template('browse-cards.html',
            search_term=search_term,
            flashcards=flashcards,
            deck=deck,
            alldecks = alldecks,
            decks=decks,
            search_logic=search_logic,
          )

@app.route('/add-deckentries/<int:deck_id>/<flashcard_ids>', methods=['POST'])
def add_deckentries(deck_id, flashcard_ids):

    flashcard_ids = [int(flashcard_id) for flashcard_id in flashcard_ids.split(',')]

    if flashcard_ids:
      for flashcard_id in flashcard_ids:
        if not DeckEntry.query.filter_by(deck_id=deck_id, flashcard_id=flashcard_id).first():
          deckentry = DeckEntry(deck_id=deck_id, flashcard_id=flashcard_id)
          db.session.add(deckentry)

      db.session.commit()
      #flash('Card(s) added to deck successfully!', 'success')
    
    return jsonify({"ok": True})

@app.route('/delete-deckentries/<int:deck_id>/<flashcard_ids>', methods=['DELETE'])
def delete_deckentries(deck_id, flashcard_ids):

    flashcard_ids = [int(flashcard_id) for flashcard_id in flashcard_ids.split(',')]

    if flashcard_ids:
      for flashcard_id in flashcard_ids:
        deckentry = DeckEntry.query.filter_by(deck_id=deck_id, flashcard_id=flashcard_id).first()
        if deckentry:
          db.session.delete(deckentry)

      db.session.commit()
      #flash('Card(s) removed from deck successfully!', 'success')
    
    return jsonify({"ok": True})
    

@app.route('/delete-deckentry/<int:deck_id>/<int:flashcard_id>', methods=['POST', 'DELETE'])
def delete_deckentry(deck_id, flashcard_id):

    deckentry = DeckEntry.query.filter_by(deck_id=deck_id, flashcard_id=flashcard_id).first()

    if deckentry:
      db.session.delete(deckentry)
      db.session.commit()

    #return jsonify({"success": True})
    return redirect(url_for('view_deck', id=deck_id))

@app.route('/view-deck/<int:id>', methods=['GET'])
def view_deck(id):
  deck = Deck.query.get_or_404(id)
  return render_template('view-deck.html',
            deck=deck,
          )

@app.route('/browse-decks', methods=['GET', 'POST'])
def browse_decks():
  
  if request.method == 'POST':
    search_term = request.form.get('search_term', '')
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', app.config['PER_PAGE'], type=int)
  else:
    search_term = request.args.get('search_term', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', app.config['PER_PAGE'], type=int)
  
  decks = Deck.query.order_by(Deck.id.desc())
  
  if search_term:
    decks = decks.filter(
        Deck.title.ilike(f"%{search_term}%") |
        Deck.description.ilike(f"%{search_term}%")
      )
  
  decks = decks.paginate(page=page, per_page=per_page, error_out=False)
  
  return render_template('browse-decks.html',
            search_term=search_term,
            decks=decks,
          )

@app.route('/add-deck', methods=['GET', 'POST'])
def add_deck():
  form = DeckForm()

  topics = Topic.query.order_by(db.func.lower(Topic.title)).all()
  form.TOPIC_ID.choices = [(topic.id, topic.title) for topic in topics]

  if form.validate_on_submit():

    try:
      deck = Deck.query.filter_by(title=form.TITLE.data, topic_id=form.TOPIC_ID.data).first()

      if not deck:
        deck = Deck(
          title=form.TITLE.data,
          description=form.DESCRIPTION.data,
          topic_id=form.TOPIC_ID.data)

        db.session.add(deck)
        db.session.commit()

        flash('Deck added successfully!', 'success')
      else:
        flash('Deck already exists!', 'warning')

      return redirect(url_for('view_deck', id=deck.id))
    except Exception as e:
      db.session.rollback()
      flash(str(e), 'danger')

  return render_template('edit-deck.html',
              form=form,
              header = "Add Deck")


@app.route('/add-deck-to-topic/<int:topic_id>', methods=['POST', 'GET'])
def add_deck_to_topic(topic_id):
  topic = Topic.query.get_or_404(topic_id)

  form = DeckForm()

  form.TOPIC_ID.choices = [(topic.id, topic.title)]

  if form.validate_on_submit():

    try:
      deck = Deck.query.filter_by(title=form.TITLE.data, topic_id=form.TITLE.data).first()

      if not deck:
        deck = Deck(
          title=form.TITLE.data,
          description=form.DESCRIPTION.data,
          topic_id=form.TOPIC_ID.data)

        db.session.add(deck)
        db.session.commit()

        flash('Deck added successfully!', 'success')
      else:
        flash('Deck already exists!', 'warning')

      return redirect(url_for('view_deck', id=deck.id))
    except Exception as e:
      db.session.rollback()
      flash(str(e), 'danger')

  return render_template('edit-deck.html',
              form=form,
              topic_id=topic_id,
              header = f"Add Deck to &#x201C;{ topic.title }&#x201D;")

@app.route('/delete-deck/<int:id>', methods=['POST', 'DELETE'])
def delete_deck(id):
  deck = Deck.query.get_or_404(id)

  try:
    topic_id = deck.topic_id
    for deckentry in deck.deckentries:
      db.session.delete(deckentry)

    db.session.delete(deck)
    db.session.commit()
    flash('Deck deleted successfully!', 'success')
    return redirect(url_for('view_topic', id=topic_id))

  except Exception as e:
    db.session.rollback()
    flash(str(e), 'danger')
    return redirect(url_for('view_deck', id=id))

@app.route('/edit-deck/<int:id>', methods=['GET', 'POST'])
def edit_deck(id):
  deck = Deck.query.get_or_404(id)

  topics = Topic.query.order_by(db.func.lower(Topic.title)).all()

  form = DeckForm(
      TITLE=deck.title,
      DESCRIPTION=deck.description,
      TOPIC_ID=deck.topic_id)

  form.TOPIC_ID.choices = [(topic.id, topic.title) for topic in topics]

  if form.validate_on_submit():

    try:
      deck.title = form.TITLE.data
      deck.description = form.DESCRIPTION.data
      deck.topic_id = form.TOPIC_ID.data

      db.session.commit()

      flash('Deck updated successfully!', 'success')
    except Exception as e:
      db.session.rollback()
      flash(str(e), 'danger')

    return redirect(url_for('view_deck', id=deck.id))

  return render_template('edit-deck.html', form=form, header = f"Edit Deck: &#x201C;{ deck.id }&#x201D;")

@app.route('/browse-topics', methods=['GET', 'POST'])
def browse_topics():

  if request.method == 'POST':
    search_term = request.form.get('search_term', '')
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', app.config['PER_PAGE'], type=int)
  else:
    search_term = request.args.get('search_term', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', app.config['PER_PAGE'], type=int)

  topics = Topic.query

  if search_term:
    topics = topics.filter(Topic.title.ilike(f"%{search_term}%"))

  topics = topics.paginate(page=page, per_page=per_page, error_out=False)

  return render_template('browse-topics.html',
            search_term=search_term,
            topics=topics,
          )

@app.route('/backup', methods=['GET', 'POST'])
def backup():
  if request.method == 'POST':
    backup_folder = app.config['BACKUP_FOLDER']
    shutil.make_archive(backup_folder, 'zip', app.config['IMAGES_FOLDER'])
    flash('Backup created successfully!', 'success')

  return render_template('backup.html')

if __name__ == '__main__':

  app.run(debug=True)
