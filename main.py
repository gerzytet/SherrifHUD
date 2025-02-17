import math
import PySimpleGUI as sg

FONT = 'Helvetica'
messages = [
    "The Joker is on the loose!",
    "Florida Polytechnic University got invaded by raccoons",
    "A giant chicken is terrorizing Lakeland",
]
# Define the layout
layout = [
    # Row for the two text boxes, with a large font
    [sg.Text('Dispatcher messages:', size=(60, 1), font=(FONT, 36))],
    [sg.Text('The Joker is on the loose!', key="message", size=(60, 2), font=(FONT, 36))],

    # Spacer between the text boxes and the bottom text line
    [sg.VPush()],

    # Row for the bottom line of text
    [sg.vbottom([sg.Text('Coordinates: ', key='coords', size=(20, 1), justification='left', font=(FONT, 28)), sg.Push(), sg.Text('Coordinates: ', key='intersection', size=(30, 1), justification='right', font=(FONT, 28))])],

    [sg.Button('QUIT')]
]

# Create the window
window = sg.Window('PySimpleGUI Demo', layout, finalize=True, resizable=True, no_titlebar=False)
window.Maximize()

intersections = [
    ((-1, -1), 'red'),
    ((0.8, 0.8), 'blue'),
    ((-0.5, 1), 'green'),
    ((0.4, -1), 'purple')
]

def nearest_intersection(point):
    distances = []
    for intersection, color in intersections:
        distance = math.sqrt((point[0] - intersection[0]) ** 2 + (point[1] - intersection[1]) ** 2)
        distances.append((distance, color, intersection))
    return min(distances)

import time
# Event loop
t = 0
while True:
    event, values = window.read(1)

    if event == sg.WINDOW_CLOSED:
        break
    if event == 'QUIT':
        break
    time.sleep(0.1)
    t += 0.1
    coords = (round(math.sin(t), 2), round(math.cos(t), 2))
    window['coords'].update(f'Coordinates: {coords}')
    distance, color, pos = nearest_intersection(coords)
    window['intersection'].update(f'Nearest Intersection: {color} at {pos}')

    window['message'].update(messages[int(t/4) % len(messages)])

# Close the window
window.close()
