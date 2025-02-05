from flask_wtf import FlaskForm
from wtforms.validators import ValidationError
from wtforms import StringField, TextAreaField, SubmitField, BooleanField, FileField, SelectField
from flask_wtf.file import FileAllowed
from wtforms.validators import DataRequired


def validate_title_and_content(form, field):
  if field.data == '':
    raise ValidationError("Both title & content must be non-empty strings")
  
class FlashcardForm(FlaskForm):
  
  TITLE = StringField('Title', validators=[])
  CONTENT = TextAreaField('Content', validators=[]) # e.g., validators=[validate_title_and_content]
  NOTES = TextAreaField('Notes', default='')
  HINT = StringField('Hint', default='')
  FLIPPABLE = BooleanField('Flippable', default=False)
  IMAGE = FileField('Upload Image', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'])])
  SUBMIT = SubmitField('Submit')

class DeckForm(FlaskForm):
  TITLE = StringField('Title', validators=[DataRequired()])
  DESCRIPTION = StringField('Description', default='')
  TOPIC_ID = SelectField('Topic', choices=[], coerce=int, default=1)
  SUBMIT = SubmitField('Submit')

class TopicForm(FlaskForm):
  TITLE = StringField('Title', validators=[DataRequired()])
  PARENT_TOPIC_ID = SelectField('Add a Parent Topic', choices=[(0, '---')], coerce=int, default=0)
  PARENT_TOPIC_ID_TO_DROP = SelectField('Drop a Parent Topic', choices=[(0, '---')], coerce=int, default=0)
  SUBMIT = SubmitField('Submit')

class GenerateImageForm(FlaskForm):
  CARD_AS_CONTEXT = BooleanField('Use Card Content as Context', default=False)
  PROMPT = TextAreaField('PROMPT', validators=[DataRequired()])
  SUBMIT = SubmitField('Submit')