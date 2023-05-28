import os

import os.path

import keyboard

import pygame

import pygame.midi as midi

import PySimpleGUI as sg


import re


#Settings path
SETTINGS_PATH = './settings.cfg'
SCAN_CODES = {1:'ESC', 2:'1', 3:'2', 4:'3', 5:'4', 6:'5', 7:'6', 8:'7', 9:'8', 10:'9',
               11:'0', 12:'-', 13:'=', 14:'<=Back', 15:'Tab', 
               16:'Q', 17:'W', 18:'E', 19:'R', 20:'T', 21:'Y', 22:'U', 23:'I', 24:'O', 25:'P', 26:'[', 27:']', 28:'_/Enter',
                 29:'CTRL', 30:'A', 31:'S', 32:'D', 33:'F', 34:'G', 35:'H', 36:'J', 37:'K', 38:'L', 39:';', 40:'\'', 41:'`', 
                 42:'LShift', 43:'\\', 44:'Z', 45:'X', 46:'C', 47:'V', 48:'B', 49:'N', 50:'M', 51:',', 52:'.', 53:'/', 54:'RShift',
                   55:'PrtSc', 56:'Alt', 57:'Space', 58:'Caps', 
                   59:'F1', 60:'F2', 61:'F3', 62:'F4', 63:'F5', 64:'F6', 65:'F7', 66:'F8', 67:'F9', 68:'F10',
                     69:'Num', 70:'Scroll', 71:'Home (7)', 72:'Up (8)', 73:'PgUp (9)', 74:'-', 75:'Left (4)', 76:'Center (5)',
                       77:'Right (6)', 78:'[+]', 79:'End (1)', 80:'Down (2)', 81:'PgDn (3)', 82:'Ins', 83:'Del'
                         }
DEBUG = True


#plain printing debugs are 
# four flaming flamingos 
# filled in, trip-lick-it
 
def verbox(txt):
    print(txt)
    

#UI translation boilerplate
langSet = 'en'
langData = {'en':{}}
def _(str, key=None):
    #if no key, clean that string so it turns into one
    key = key if key else re.sub(r'\W+', '', str.strip().lower())
    if key in langData[langSet]:
        return langData[langSet][key]
    return str

class MTKB():

    def __init__(self):
        sg.theme('DarkGreen')
        pygame.init()
        
        # make a button and store it 
        def pianoKeyBtn(text = "", key = None, size=None, button_color = None):
            self.pianoKeys[key] = sg.Button('', key = f"^{key}", size=size, button_color = button_color)
            self.pianoKeys[key].default_color = button_color
            return self.pianoKeys[key]

        # make a button and store it 
        def scancodeBtn(val, key = None, button_color = None, size=None):
            key = F"{key}".lower()
            btn = sg.Button(f"{val}", key = F"{key}", button_color = button_color if button_color is not None else sg.DEFAULT_BUTTON_COLOR, size=size if size else (3,3), pad =(0,0)  )
            self.keybdBtns[F"{key}"] = btn
            return btn



        self.locked = False        
        # used while testing & with zombies locking up the port 
        # open(".lock","w").close()
        # self.locked = True 
        
        # if ( os.path.exists('.lock') ):
        #     print("Lock file exists, graceful shutdown fail")
        #     return

        self.daemon = MTKB_Daemon()
        #or just this
        midi.init()

        keyboard.hook(self.keyboardHook)

        #todo - get more scan code datasets, this is just a "standard" US keyboard
        #todo - after, make a menu to select them


        self.config = {}
        self.chordSet = "" #numericallidiction
        self.captureKey = 59        
        self.chooseCapture = False
        self.recKeysMode = False
        self.midiMode = False
        self.selectedScanCode = False
        self.lastKeybdBtn = None
        self.pianoKeys = {}
        self.keybdBtns = {}
        self.codeChords = {}
        self.pianoKeysPressed = []
        


        white = [0, 2, 4, 5, 7, 9, 11]
        self.whiteKeys = white
        #black = [1, 3, 6, 8, 10]

        (inputs,outputs) = self.getMidiDevices()
        config = sg.user_settings_load('./settings.cfg')        
        self.config = config['config'] 
        #empty settings file
 
        if not self.config.get('midiToKey'):
 #           print("MTSetup")
            self.config['midiToKey'] = 'midiToKey'
            self.config['midiConnect'] = {}
            self.config['midiConnect']['midiIn'] = 0
            self.config['midiConnect']['midiOut'] = 0
            self.config['codeChords'] = {}

            sg.user_settings_save(SETTINGS_PATH)

        if self.config.get('codeChords'):
                #print("got chords")
                self.codeChords=self.config['codeChords']
                #print(self.codeChords)


        (midiIn, midiOut )=(self.config['midiConnect']['midiIn'],self.config['midiConnect']['midiOut'])     
        self.keystrokes = ['']

        #a crude piano key set of 12
        midiOptions = [         ]
        #functionality
        midiOptions.append([sg.Text("INPUT",justification="left"),sg.OptionMenu(k='_midiIn',tooltip="INPUT",values=inputs, default_value = midiIn if midiIn in inputs else inputs[-1] )])
        midiOptions.append([sg.Text("OUTPUT",justification="left"),sg.OptionMenu(k='_midiOut',values=outputs, default_value = midiOut if midiOut in outputs else outputs[-1])])

            
        self.thruBtn = sg.Button( _('Midi Thru'),k='_midiThru')

        self.recMidiBtn = sg.Button( _('MIDI Capture'), k='_recMidiToggle')
        
        self.recKeysBtn = sg.Button( _('Keyboard Capture'), k='_recKeysToggle')
        
        self.readyBtn = sg.Button( _('MIDI'), k='_ready')
        self.connectBtn = sg.Button( _('Connect'),k='_connect')
        
        self.disconnectBtn = sg.Button( _('Disconnect'),k='_disconnect',disabled=True)


        midiOptions.append(
                    [
                       sg.Text( _('MIDI:')) , 
                       self.connectBtn, 
                       self.disconnectBtn,
                       self.thruBtn, 
                       self.recMidiBtn, 
                       self.recKeysBtn,
                       sg.Text( _('Settings') ),
                       sg.Button(_('Save'),k='save'),
                       sg.Button(_('Load'),k='load') 
                    ])

        #lazy slice and dice the scancodes into rows of buttons
        
        # layout.append(scancodeBtn(f'{key}', key=val) for val,key in list(SCAN_CODES.items())[58:68])
        # layout.append(scancodeBtn(f'{key}', key=val) for val,key in list(SCAN_CODES.items())[:14])
        # layout.append(scancodeBtn(f'{key}', key=val) for val,key in list(SCAN_CODES.items())[14:28])
        # layout.append(scancodeBtn(f'{ ddddddkey}', key=val) for val,key in list(SCAN_CODES.items())[28:41])
        # layout.append(scancodeBtn(f'{key}', key=val) for val,key in list(SCAN_CODES.items())[41:54])
        # layout.append(
        #     scancodeBtn(f'{key}', key=val, size=(5,3)) for val,key in list(SCAN_CODES.items())[54:58]
        # )
                                     
        # layout.append(scancodeBtn(f'{key}', key=val, size=(8,2)) for val,key in list(SCAN_CODES.items())[68:72])
        # layout.append(scancodeBtn(f'{key}', key=val, size=(8,2)) for val,key in list(SCAN_CODES.items())[72:77])
        # layout.append(scancodeBtn(f'{key}', key=val, size=(8,2)) for val,key in list(SCAN_CODES.items())[77:])
 
        
        self.chooseCapBtn = sg.Button(_('Choose Capture Key'),k='_chooseCaptureKey',expand_x=True)

        self.keystrokeList = sg.Listbox(values=self.keystrokes, size = (50,200), auto_size_text = True)

        self.statusBar = sg.Text("")
        self.verbLines = sg.Multiline("""Chord2Key::
Select your MIDI Device from the inputs 
Select an Output - required for passthru -  

Use [MIDI Capture] to set the MIDI note/chord to record,
or use the GUI keys to toggle the keys you want as your trip.

Use [Keyboard Capture] to record keystrokes for your selcection.

Currently a modulus 12 is used on the note number, simply to simplify entering chords.

"""
                                        ,size=(50,100),write_only=True, reroute_stdout=True)

        midiValues = sg.user_settings_get_entry('midiConnect')

        self.verbLines
        
        layout =[
                [
                    sg.Frame(
                            '',
                            [ [pianoKeyBtn("",key=key, size=(2,4), button_color = '#eeeeee' if key in white else '#000000' ) for key in range(0,12)]  ]
                             )
                ],
                [
                   sg.Frame('', midiOptions, vertical_alignment="top")
                ],
                [
                    sg.Frame('',[[self.chooseCapBtn],[sg.Text("Keystrokes")],[self.keystrokeList] ], vertical_alignment="top",size=(240,400))
                , 
                    sg.Frame('',[[self.statusBar],[self.verbLines]], vertical_alignment="top", size=(380,400)) 
                ]
                ]
        layout = [ [ sg.Frame('Chord2Key/stroke~>smell-of-burnt-taoist',layout)]]
        self.factory(layout)
        

    def factory(self,layout):
        window = sg.Window('MIDItoKB', layout, alpha_channel=0.9, location=(0,0), size=(1024,768), margins=(20,20), resizable=True, finalize=True)        
        self.window = window
        self.layout = layout
        #factory gears -  glue twixt the view & model - aeroplane gooloo hehehahahebblbshit ummm - Nothing to see here! Move along.
        while True:
            event,  values = window.read()
            self.statusBar.update(self.statusBarText())
#            self.keystrokeList.update(values=self.keystrokes)

            if event == sg.WIN_CLOSED:
                break
            else:
                sEvent = F"{event}"
                if sEvent.isnumeric():
                    print("DEFUNC?")
                    #self.scanCodeSet(sEvent)
                    continue

                if sEvent[0]=='^':
                    sEvent = sEvent[1:]
                    nEvent = int(sEvent)
                    self.midiBtnPress(nEvent)
                    continue
                
                sEvent = sEvent[1:] if sEvent[0]=='_' else sEvent
                if hasattr(self,sEvent): 
                    #my microFhactory[tm]}:'P  
                    #object to fill with options passed to function named by its key/ the event value strignified sEvent
                    dic = {}
                    for k, v in values.items():
                        k=F"{k}"
                        #split numerics from MIDI device selects,
                        #split numerics from MIDI device selects,
                        #buid a dict for the named func call
                        if type(v) == type(""):
                            spill = v.split('::')
                            if k[0] == '_':
                                dic[ k[1:]  ] = v
                            if len(spill) > 1:
                                if spill[0].isnumeric():
                                    spill[0] = int(spill[0])
                                dic[ k[1:] ] = spill[0] 

                    #get the method / 'attribute' from this class
                    attr = getattr(self,sEvent)
                    if attr:
                        attr(dic)

                

                

        window.close()


    def keyboardHook(self,event):
        #(ev_type, ev_key)= (event.event_type, event.scan_code)
        #print(event.event_type, self.chooseCapture)
        if self.chooseCapture and event.event_type == "up":
            self.captureKey = event.scan_code
            self.chooseCapture = False
            self.chooseCapBtn.update(button_color = sg.DEFAULT_BUTTON_COLOR)
            self.statusBar.update(self.statusBarText())
            return
        

        #print((event.scan_code,self.captureKey == event.scan_code))

        if event.scan_code == self.captureKey:
            if event.event_type == "up":
                self.recKeysToggle(event)
            return

        if self.recKeysMode and self.chordSet:
            #print(F"keyboardHook:{self.chordSet} ->> {event}")
            self.keystrokes.append(F"{event.event_type}::{event.name}::{event.scan_code}")
            self.setCodeChord(self.chordSet,self.keystrokes)
            #self.codeChords[self.chordSet]=self.keystrokes
            self.updateKeystrokeList()
        
        self.statusBar.update(self.statusBarText())


    def getCodeChord(self,chordValue):
        return self.codeChords[F"{chordValue}"] if self.codeChords.get(F"{chordValue}") else [] 
    
    def setCodeChord(self,chordValue,strokes):
        self.codeChords[F"{chordValue}"] = strokes            
#######factory##functions#########################################################################

    def chooseCaptureKey(self, event):
        self.chooseCapBtn.update(button_color = 'red')
        self.chooseCapture = True
        sg.popup_timed(("Press the key you want to use to toggle recording.","recKeyPress"),auto_close_duration=1)
        


    #handle on screen piano button actions
    def midiBtnPress(self,nEvent):

        if nEvent not in self.pianoKeysPressed:
            self.pianoKeysPressed.append(nEvent)
        else:
            self.pianoKeysPressed.remove(nEvent)

        tot = 0
        for i in self.pianoKeysPressed:
            tot = tot + 2**i

        self.pianoKeysUpdate(tot)

    def midiThru(self,event):
        if self.daemon:
            self.daemon.midiThru = not self.daemon.midiThru
            self.thruBtn.update(button_color = 'green' if self.daemon.midiThru else sg.DEFAULT_BUTTON_COLOR)

    def recMidiToggle(self,event):
        self.midiMode = not self.midiMode
        self.recMidiBtn.update(button_color = 'red' if self.midiMode else sg.DEFAULT_BUTTON_COLOR)
    
    def recKeysToggle(self,event):
        self.recKeysMode = not self.recKeysMode
        if self.recKeysMode:
            self.keystrokes = []
            self.keystrokeList.update(values = self.keystrokes)
        else:
            if self.chordSet and len(self.keystrokes):
                self.setCodeChord(self.chordSet,self.keystrokes)
                #self.codeChords[self.chordSet] = self.keystrokes
                self.recKeysBtn.update(button_color = sg.DEFAULT_BUTTON_COLOR)
                self.config['codeChords'] = self.codeChords
                sg.user_settings_set_entry('config',self.config)
                sg.user_settings_save(SETTINGS_PATH)
                return
            
        self.recKeysBtn.update(button_color = 'red' if self.recKeysMode else sg.DEFAULT_BUTTON_COLOR)
    
    #update the chord/note associated with a keyboard scan code
    def scanCodeSet(self, sEvent):
        #defunct
        return
        
    def updateKeystrokeList(self):
        self.keystrokeList.update(values = self.codeChords[self.chordSet] if self.codeChords.get(self.chordSet) else ["[RECORD KEYSTROKES]"])


    def pianoKeysUpdate(self, value):
        button_colors = [  ['#666666','#000000'],
        ['#808080','#FFffFF'] ]
        value = int(value)
        for i in range(12):
            button_color = button_colors[1 if i in self.whiteKeys  else 0][0 if value&2**i else 1]
            self.pianoKeys[i].update(button_color = button_color )
        
        self.chordSet = F"{value}"

        self.updateKeystrokeList()
                     
        #self.config['codeChords'] = self.codeChords
        #sg.user_settings_set_entry('config',self.config)
        #sg.user_settings_save(SETTINGS_PATH)

    def connect(self,values = False):
        del(self.daemon)

        self.daemon = MTKB_Daemon(Client = self)


        if values == False:
            return
        
        self.config['midiConnect'] = values
        sg.user_settings_set_entry('config',self.config)
        sg.user_settings_save(SETTINGS_PATH)

        inPort = values['midiIn']
        outPort = values['midiOut']

        #try try try
        if midi.get_init():
            midi.quit()

        if not midi.get_init():
            midi.init()

        try:
            midiIn = midi.Input(inPort)
            midiIn.poll()
        except:
            sg.popup_auto_close("MIDI Input failed! Device maybe in use?")
            verbox(F"\"{inPort}\" ::  midi.Input() I/O error")
            return

        
        self.connectBtn.update(disabled=True)
        self.disconnectBtn.update(disabled=False)
        
        #midiOut = -999
        try:
            midiOut = midi.Output(outPort)
            midiOut.note_off(0,0)
        except:
            sg.popup_auto_close("MIDI Output failed, and all you got was this awful error")
            verbox("the O end in porcelean")
        
        #and even then
        # if hooked, unhook, it was all a test suka
        if midi.get_init():
            midi.quit()

        #now we 'safe fly' start daemon
        verbox(F"MIDI connect initiated.")

        self.daemon.start( (inPort,outPort) )


    def disconnect(self,values):
        verbox("<- ->")
        self.connectBtn.update(disabled=False)
        self.disconnectBtn.update(disabled=True)
        #pygame.quit()
        self.daemon.stop()
        verbox("-><-")
    
    def getMidiDevices(self):
        inputs = []
        outputs = []
        for i in range(midi.get_count()):
            device_info = midi.get_device_info(i)
            if device_info[2] == 1:
                inputs.append(F"{i}::{device_info[1].decode('utf-8')}")
            if device_info[3] == 1:
                outputs.append(F"{i}::{device_info[1].decode('utf-8')}")
        return (inputs,outputs)
    
    def statusBarText(self):        
        txt = F"Capture Key: {SCAN_CODES[self.captureKey]} | Record Keys: {'On' if self.recKeysMode else 'Off'} Mode: {'Keystroke Playback' if self.midiMode else 'Keystroke Rec.'}"
        return txt



import threading
class MTKB_Daemon():

    def __init__(self, Client = None, modulus = 12):
        #debuggery(userInterface)
        self.mod = modulus
        self.client = Client
        self.inTheLoop = False
        self.keepAlive = True
        self.midiIn = None
        self.midiOut = None
        self.midiThru = True
        self.thread = threading.Thread(target=self.poll)

    def start(self,ioPorts):
        if self.inTheLoop:
            #don't start what you haven't called destruct on
            return
        
        verbox("starting MIDI daemon")

        if not midi.get_init():
            midi.quit()
        midi.init()


        #prints started polling
        self.ioPorts = (midiInPort, midiOutPort) = ioPorts
        self.midi = midi
        self.midiIn = midi.Input( midiInPort )
        self.midiInPort = midiInPort

        if (midiOutPort>0):
            self.midiOut = midi.Output(  midiOutPort )
        self.thread.start()
        #debuggery("daemon@start:thread.start invoked")
        verbox(F"In::{midiInPort} Out::{midiOutPort}  initialised :{midi.get_init()}")

    def stop(self):
        self.inTheLoop = self.keepAlive = False
        pygame.quit() 
        pygame.init()
        self.thread._stop()

        
    def poll(self):
        verbox("started polling.")
        keysDown = 0
        notes = []  

        while self.keepAlive:
            #so we know we're inside the keepalive loop
            self.inTheLoop = True

            if self.midiIn.poll():
                
                msg=self.midiIn.read(1) 
                if self.midiOut and self.midiThru:
                    self.midiOut.write(msg)
                msg = msg[0][0]
                
                verbox(msg)
                dir = "up" if msg[0] == 128 else "down"
                note = msg[1] % self.mod
                #debuggery(F"midi-read:{note}")
                if dir == "down":                                                     
                    tot = 0
                    keysDown+=1
                    notes.append(note)
                    for i in notes:
                        tot += 2**i
                if dir == "up":
                    keysDown-=1
                    
                if keysDown == 0:
                    tot = 0
                    for i in notes:
                        tot += 2**i
                    
                    sTot = F"{tot}"
                    strokes = self.client.getCodeChord(sTot)
                    print(F"keys-- {tot}")
                    #print(self.client.codeChords)
                    print(strokes)
                    if strokes:
                        for key in strokes:
                            bits = key.split("::")
                            if bits[0] and bits[1]:
                                ke = keyboard.KeyboardEvent(bits[0],bits[1])
                                keyboard.play([ke])
                        

                    if self.client.midiMode:
                        #self.client.chordSet = sTot
                        self.client.pianoKeysUpdate(sTot)

                    notes = []


if __name__ == "__main__":
    MTKB()
    
    # #it's all over
    # if mtkb.locked is True:
    #     os.remove('./.lock')
