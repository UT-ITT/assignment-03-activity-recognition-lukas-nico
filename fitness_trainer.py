# this program visualizes activities with pyglet

import activity_recognizer as activity
import pyglet

loaded = False
recognizer = None
images = {}
sprites = {}
labels = {}
times = {
        "jumpingjack": 0,
        "lifting": 0,
        "rowing": 0,
        "running": 0
    }

current_time = 0
current_action = None

# Load images
def load_xcentered_image(name):
    image = pyglet.image.load(f'./img/{name}.png')
    image.anchor_x = image.width // 2
    return image

def load_centered_images(name):
    image1 = load_xcentered_image(name+'_1')
    image2 = load_xcentered_image(name+'_2')
    return [image1,image2]

def load_images():
    global images
    images = {
        "jumpingjack": load_centered_images("jumpingjack"),
        "lifting":     load_centered_images("lifting"),
        "rowing":      load_centered_images("rowing"),
        "running":     load_centered_images("running"),
        "?":           [create_text_image("?", 550, 260), create_text_image("?", 560, 320)]
    }

def create_text_image(text, size, y_offset, color=(0,0,0)):
    label = pyglet.text.Label(text,
                          font_name='Times New Roman',
                          font_size=size,
                          color=color
                          )
    window.clear()
    label.draw()
    w = label.content_width
    h = label.content_height

    buffer = pyglet.image.get_buffer_manager().get_color_buffer()
    texture = buffer.get_region(0, 0, w, h).get_texture()

    texture.anchor_x = texture.width // 2
    texture.anchor_y = - y_offset

    return texture

title = 'Fitness Trainer'
window = pyglet.window.Window(width=1400, height=1024, caption=title)
pyglet.gl.glClearColor(0.2,0.2,0.2,1)

title_label = pyglet.text.Label(title,
                          font_name='Times New Roman',
                          font_size=48,
                          x=window.width//2, y=window.height - 50,
                          anchor_x='center', anchor_y='center',
                          color=(255,255,255)
                          )

loading_label = pyglet.text.Label("Loading please wait ...",
                          font_name='Times New Roman',
                          font_size=48,
                          x=window.width//2, y=window.height // 2 - 48,
                          anchor_x='center', anchor_y='center',
                          color=(255,255,255)
                          )

line_y = window.height * 0.4
line = pyglet.shapes.Line(0, line_y, window.width, line_y, thickness=4, color=(170,170,170))

def create_sprite(name,x,y,scale=0.1):
    sprite = pyglet.sprite.Sprite(img=images[name][0], x=x, y =y)
    sprite.scale = scale
    sprite.name = name
    sprite.frame = 0
    return sprite

def create_sprites():
    global sprites
    sprites = {
        "jumpingjack": create_sprite("jumpingjack", window.width * 1/5, line_y/2),
        "lifting":     create_sprite("lifting", window.width * 2/5, line_y/2),
        "rowing":      create_sprite("rowing", window.width * 3/5, line_y/2),
        "running":     create_sprite("running", window.width * 4/5, line_y/2),
        "current":     create_sprite("?", window.width / 2, line_y + (window.height - line_y)/2 - 50, 0.2)
    }

def create_label(text, x, y, size=20):
    return pyglet.text.Label(text,
                          font_name='Times New Roman',
                          font_size=size,
                          x=x,
                          y=y,
                          anchor_x='center', anchor_y='center',
                          color=(255,255,255)
                          )

def create_labels_for_action(name, x):
    distance_img = line_y/2 - 50
    distance_text = distance_img - 60
    return {
                "name": create_label(name.capitalize(), x, distance_img, 30),
                "time": create_label("Overall time: 0s", x, distance_text)
            }

def create_labels():
    global labels
    current_y = line_y + (window.height - line_y)/2 - 110
    current_x = window.width / 2
    labels = {
        "jumpingjack": create_labels_for_action("jumpingjack", window.width * 1/5),
        "lifting":     create_labels_for_action("lifting", window.width * 2/5),
        "rowing":      create_labels_for_action("rowing", window.width * 3/5),
        "running":     create_labels_for_action("running", window.width * 4/5),
        "current": {
                "name": create_label("No action was detected", current_x, current_y, 40),
                "time": create_label("Doing since: 0s", current_x, current_y - 80, 30)
                #"accuracy": create_label("Accuracy: 0%", current_x, current_y - 140, 30)
            }
    }
    labels["current"]["time"].visible = False
    #labels["current"]["accuracy"].visible = False

def load(delta):
    global loaded, recognizer
    if not loaded:
        recognizer = Recognizer()
        load_images()
        create_sprites()
        create_labels()
        loaded = True

def update_current_activity(prediction):
    global sprites, labels, current_action, current_time

    # Save workout times
    if current_action in times:
        seconds = round(current_time / 60)
        times[current_action] += seconds
        labels[current_action]["time"].text = f"Overall time: {times[current_action]}s"

    # Update to new action
    current_action = prediction
    current_time = 0

    # Update ui
    if current_action is None:
        sprites["current"].name = "?"
        labels["current"]["name"].text = "No action was detected"
        labels["current"]["time"].visible = False
    else:
        sprites["current"].name = current_action
        labels["current"]["name"].text = current_action.capitalize()

        labels["current"]["time"].text = "Doing since: 0s"
        labels["current"]["time"].visible = True

    # Update the sprite
    sprites["current"].image = images[sprites["current"].name][sprites["current"].frame]


def update(delta):
    # Check that everything is loaded
    global loaded, current_action, current_time
    if not loaded:
        return

    prediction = recognizer.predict()

    # Check if the action is still the same
    if prediction == current_action:
        if not prediction:
            return

        current_time += 1

        labels["current"]["time"].text = f"Doing since: {current_time // 60}s"

    else:
        update_current_activity(prediction)

sprite_states = 2
current_sprite_state = 0
def animateSprites(delta):
    global sprites, images
    for sprite in sprites.values():
        sprite.frame = (sprite.frame + 1) % len(images[sprite.name])
        sprite.image = images[sprite.name][sprite.frame]

@window.event
def on_draw():
    window.clear()
    global loaded

    if loaded:
        title_label.draw()

        for sprite in sprites.values():
            sprite.draw()

        for action in labels.values():
            for label in action.values():
                label.draw()

        line.draw()
    else:
        loading_label.draw()

class Recognizer:
    def __init__(self):
        # Wir starten den Frame-Zähler bei 0
        self.frame_count = 0
    def predict(self):
        self.frame_count += 1

        # 60 Frames pro Sekunde (60 Hz)
        # 1. Die ersten 3 Sekunden -> None (0 bis 180 Frames)
        if self.frame_count < 3 * 60:
            return None

        # 2. Die nächsten 5 Sekunden -> "jumpingjack" (181 bis 480 Frames)
        # (3s Start + 5s Dauer = 8 Sekunden insgesamt)
        elif self.frame_count < (3 + 5) * 60:
            return "jumpingjack"

        # 3. Danach für 3 Sekunden -> "rowing" (481 bis 660 Frames)
        # (8s Start + 3s Dauer = 11 Sekunden insgesamt)
        elif self.frame_count < (3 + 5 + 3) * 60:
            return "rowing"

        # Optional: Nach dem Testlauf wieder auf None schalten
        else:
            return None

pyglet.clock.schedule_interval(update, 1/60)
pyglet.clock.schedule_interval(animateSprites, 1)
# Delay the loading of the sprites to show a loading screen
pyglet.clock.schedule_once(load, 1.0)
pyglet.app.run()
