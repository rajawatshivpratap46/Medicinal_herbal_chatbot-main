<<<<<<< HEAD
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import base64

# List of classes your model can identify
class_names = ['Aloe Vera', 'Amla', 'Beetroot', 'Tulsi', 'Turmeric', 'Ginger', 
               'Chamomile', 'Boswellia', 'Garlic', 'Lemon Peel', 'Moringa', 
               'Peppermint', 'Spirulina', 'White Willow Bark', 'Willow Bark']

def load_model():
    """Load the pre-trained MobileNet model"""
    # You can use MobileNetV2 pre-trained on ImageNet and fine-tune it
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze the base model layers
    base_model.trainable = False
    
    # Add classification head
    model = tf.keras.Sequential([
        base_model,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(len(class_names), activation='softmax')
    ])
    
    # If you have a saved model, you can load it instead
    # model = tf.keras.models.load_model('herb_identifier.h5')
    
    return model

def preprocess_image(image_data):
    """Preprocess image for model prediction"""
    # Handle base64 encoded images
    if isinstance(image_data, str) and image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
        image_data = base64.b64decode(image_data)
    
    # Open image from binary data
    img = Image.open(io.BytesIO(image_data))
    
    # Resize image to expected dimensions
    img = img.resize((224, 224))
    
    # Convert to array and normalize
    img_array = tf.keras.preprocessing.image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
    
    return img_array

def predict_herb(model, image_data):
    """Make a prediction with the model"""
    # Preprocess the image
    processed_image = preprocess_image(image_data)
    
    # Make prediction
    predictions = model.predict(processed_image)
    
    # Get the predicted class and confidence
    predicted_class_index = np.argmax(predictions[0])
    confidence = float(predictions[0][predicted_class_index])
    
    # Get the class name
    herb_name = class_names[predicted_class_index]
    
    return {
        'herbName': herb_name,
        'confidence': confidence,
        'success': True
    }
=======
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import base64

# List of classes your model can identify
class_names = ['Aloe Vera', 'Amla', 'Beetroot', 'Tulsi', 'Turmeric', 'Ginger', 
               'Chamomile', 'Boswellia', 'Garlic', 'Lemon Peel', 'Moringa', 
               'Peppermint', 'Spirulina', 'White Willow Bark', 'Willow Bark']

def load_model():
    """Load the pre-trained MobileNet model"""
    # You can use MobileNetV2 pre-trained on ImageNet and fine-tune it
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze the base model layers
    base_model.trainable = False
    
    # Add classification head
    model = tf.keras.Sequential([
        base_model,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(len(class_names), activation='softmax')
    ])
    
    # If you have a saved model, you can load it instead
    # model = tf.keras.models.load_model('herb_identifier.h5')
    
    return model

def preprocess_image(image_data):
    """Preprocess image for model prediction"""
    # Handle base64 encoded images
    if isinstance(image_data, str) and image_data.startswith('data:image'):
        image_data = image_data.split(',')[1]
        image_data = base64.b64decode(image_data)
    
    # Open image from binary data
    img = Image.open(io.BytesIO(image_data))
    
    # Resize image to expected dimensions
    img = img.resize((224, 224))
    
    # Convert to array and normalize
    img_array = tf.keras.preprocessing.image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
    
    return img_array

def predict_herb(model, image_data):
    """Make a prediction with the model"""
    # Preprocess the image
    processed_image = preprocess_image(image_data)
    
    # Make prediction
    predictions = model.predict(processed_image)
    
    # Get the predicted class and confidence
    predicted_class_index = np.argmax(predictions[0])
    confidence = float(predictions[0][predicted_class_index])
    
    # Get the class name
    herb_name = class_names[predicted_class_index]
    
    return {
        'herbName': herb_name,
        'confidence': confidence,
        'success': True
    }
>>>>>>> 2f643665ff2ea095b3b978e8517d08f667d854b2
