import math
import PySimpleGUI as sg

FONT = 'Helvetica'
# Define the layout
layout = [
    # Row for the two text boxes, with a large font
    [sg.Text('Text Box 1:', size=(60, 1), font=(FONT, 18))],
    [sg.Text('Text Box 2:', size=(60, 1), font=(FONT, 18))],

    # Spacer between the text boxes and the bottom text line
    [sg.VPush()],

    # Row for the bottom line of text
    [sg.vbottom([sg.Text('Coordinates: ', key='coords', size=(40, 1), justification='left', font=(FONT, 14)), sg.Push(), sg.Text('Coordinates: ', key='intersection', size=(40, 1), justification='right', font=(FONT, 14))])]
]

# Create the window
window = sg.Window('PySimpleGUI Demo', layout, finalize=True, resizable=True, no_titlebar=False)
window.Maximize()

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

# Close the window
window.close()
