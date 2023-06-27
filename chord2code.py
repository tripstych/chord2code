import os

import os.path

import keyboard

import pygame

import pygame.midi as midi

import PySimpleGUI as sg


import re


ACTIVE_COLOR = "#a0a0f0"

#Settings path
SETTINGS_PATH = './settings.cfg'


INTRO_TEXT ="""::Chord2Key::
Select & connect a MIDI device,
capture notes or chords and assign a 
list of keystrokes / scancodes
to have them playback.  
Turn the MIDI capture off when 
you're done, Playback mode is
disabled until then.

Alternatively, use the GUI keyboard keys
to toggle the keys you want as your trigger.

Use the [Keyboard Capture] button, or press
an assigned keyboard key, to start and stop
recording keystrokes. The currently assigned
hotkey is shown in the status bar above.


"""

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
        sg.theme('darkblue')
        #sg.set_options(button_color = "#ffffff")
        pygame.init()
        bwKeyNames = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        # make a button and store it 
        def pianoKeyBtn(text = "", key = None, size=None, button_color = None):
            self.pianoKeys[key] = sg.Button(bwKeyNames[key],key = f"^{key}", size=size, button_color = button_color)
            return self.pianoKeys[key]

        # make a button and store it 
        def scanCodeBtn(val, key = None, button_color = None, size=None):
            key = F"{key}".lower()
            btn = sg.Button(f"{val}", key = F"{key}", button_color = button_color if button_color is not None else sg.DEFAULT_BUTTON_COLOR, size=size if size else (3,3), pad =(0,0)  )
            self.keybdBtns[F"{key}"] = btn
            return btn



        self.locked = False        
        # used while testing & with zombies locking up the port 
        # open(".lock","w").close()
        # self.locked = True 
        self.inTheLoop = False

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
        self.connectState = False
        self.chordSet = "" #numericallidiction
        self.daemon = False
        self.playbackDisabled = False
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
        self.midiThruState = True


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

        if self.config.get('autoConn'):
            self.autoConn = self.config['autoConn']
        else:
            self.autoConn = True

        if self.config['midiConnect']:
            
            if not self.config['midiConnect'].get('midiIn'):
                self.config['midiConnect']['midiIn']=0
            if not self.config['midiConnect'].get('midiOut'):
                self.config['midiConnect']['midiOut']=0

        (midiIn, midiOut )=(self.config['midiConnect']['midiIn'],self.config['midiConnect']['midiOut'])     
        


        self.keystrokes = ['']

        midiOptions = [         ]
        #functionality
        self.midiInOpt = sg.OptionMenu(k='_midiIn',tooltip="INPUT",values=inputs, default_value = "".join(list(filter(lambda a: F"{midiIn}::" in a, inputs))) )
        self.midiOutOpt = sg.OptionMenu(k='_midiOut',values=outputs, default_value = "".join(list(filter(lambda a: F"{midiOut}::" in a, outputs))) )

        self.autoConnCB = sg.Checkbox("Auto Connect",default=self.autoConn, tooltip="Connect when opened",k='_autoConnToggle',enable_events=True)


        midiOptions.append([self.autoConnCB,sg.Text("modulus"),sg.Input("12",key="modulus",size=2),sg.Text("offset note"),sg.Input("0",key="offset",size=2),
                        sg.Text("INPUT",justification="left"), self.midiInOpt,sg.Text("OUTPUT",justification="left"), self.midiOutOpt])
            
        self.thruBtn = sg.Button( _('Midi Thru'),k='_midiThru',button_color=ACTIVE_COLOR)

        self.recMidiBtn = sg.Button( _('MIDI Capture'), k='_recMidiToggle')

        self.recKeysBtn = sg.Button( _('Keyboard Capture'), k='_recKeysToggle')
        
        self.readyBtn = sg.Button( _('MIDI'), k='_ready')
        self.connectBtn = sg.Button( _('Connect'),k='_connect')
        

        
        #self.disconnectBtn = sg.Button ( _('Disconnect'),k='_disconnect',disabled=True)


        midiOptions.append(
                    [
                       sg.Text( _('MIDI:')) , 
                       self.connectBtn, 
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
        self.disablePlaybackBtn = sg.Button(_('Disable Playback'),k='_disablePlayback',expand_x=True )
        self.keystrokeList = sg.Listbox(values=self.keystrokes, size = (26,40))

        self.removeKeystrokeBtn = sg.Button(_('Ꭓ'),k='_removeKeystroke',expand_x=True)
        self.clearKeystrokesBtn = sg.Button(_('Clear Keystrokes'),k='_clearKeystrokes',expand_x=True)
        

        self.statusBar = sg.Text(self.statusBarText())
        self.verbLines = sg.Multiline(INTRO_TEXT,font="Serif 12",autoscroll=True,text_color="#ffffff",size=(50,50),write_only=True, reroute_stdout=True)

        pksFrame = sg.Frame(
                            '',
                            [ [pianoKeyBtn("",key=key, size=(2,4), button_color = '#eeeeee' if key in white else '#000000' ) for key in range(0,12)]  ],
                            key = 'pianoKeys',
                            visible=True
                             )        
        
        midiFrame = sg.Frame('', midiOptions, vertical_alignment="top",visible=True)
        captureFrame = sg.Frame('',[[self.disablePlaybackBtn],[self.chooseCapBtn],[self.clearKeystrokesBtn] ,[sg.Text("Keystrokes")],
                                    [self.keystrokeList,self.removeKeystrokeBtn] ], vertical_alignment="top",size=(240,300),
                                     key = 'captureKeys',
                                      visible=True)
        infoFrame = sg.Frame('',[[self.statusBar],[self.verbLines]], vertical_alignment="top", size=(380,400),
                             key = 'infoFrame',
                             visible=True)
        
        layout =[
                 [
                    pksFrame
                ],
                   [
                   midiFrame
                ],
             
                [
                    captureFrame
                , 
                    infoFrame 
                ]
                ]
        
        outlayout = [ 
                    [sg.Frame('Chord2KeyStroke;. do you smell-burnt-taoist?',
                                 layout,element_justification="center", 
                                 vertical_alignment="center", 
                                 expand_y=True, 
                                 expand_x=True)
                    ]]

        self.factory((layout,outlayout))
        

    def factory(self,box):
        (layout,outlayout)=box

        window = sg.Window('MIDItoKB', outlayout, alpha_channel=0.9, location=(0,0), size=(800,600), margins=(20,20), resizable=True, finalize=True)        
        self.window = window  
        self.layout = layout

        

        #factory gears -  gloo for the view 
        while True:
            event,  values = window.read()

            if event == sg.WIN_CLOSED:
                break

            self.inTheLoop = True
            if values is None:
                continue
            
            for k in values.keys():
                kS=F"{k}"
                if kS[0]=='#':
                    z = kS[1:]
                    val=values[kS]
                    if hasattr(self,z):
                        print(z,val,">>>>,")
                        self.__setattr__(z,val)
            self.statusBar.update(self.statusBarText())
            
#            self.keystrokeList.update(values=self.keystrokes)
        
            sEvent = F"{event}"
            if sEvent.isnumeric():
                verbox("DEFUNC?")
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
                    #buid a dict for the named func call
                    if type(v) == type(""):
                        spill = v.split('::')
                        #for midi list/option values
                        if k[0] == '_':
                            dic[ k[1:] ] = v
                        if len(spill) > 1:
                            if spill[0].isnumeric():
                                spill[0] = int(spill[0])
                            dic[ k[1:] ] = spill[0] 

                #get the method / 'attribute' from this class
                attr = getattr(self,sEvent)
                if attr:
                    attr(dic)

        window.close()

    def autoConnToggle(self,vals): 
        self.autoConn = not self.autoConn
        print(vals,'autocmmmm;',self.autoConn)

    def keyboardHook(self,event):
        #(ev_type, ev_key)= (event.event_type, event.scan_code)
        #verbox(event.event_type, self.chooseCapture)
        if self.chooseCapture and event.event_type == "up":
            self.captureKey = event.scan_code
            self.chooseCapture = False
            self.chooseCapBtn.update(button_color = sg.DEFAULT_BUTTON_COLOR)
            #if (self.inTheLoop):
            #self.statusBar.update(self.statusBarText())
            return
        

        #verbox((event.scan_code,self.captureKey == event.scan_code))

        if event.scan_code == self.captureKey:
            if event.event_type == "up":
                self.recKeysToggle(event)
            return

        if self.recKeysMode and self.chordSet:
            #verbox(F"keyboardHook:{self.chordSet} ->> {event}")
            self.keystrokes.append(F"{event.event_type}::{event.name}::{event.scan_code}")
            self.setCodeChord(self.chordSet,self.keystrokes)
            #self.codeChords[self.chordSet]=self.keystrokes
            self.updateKeystrokeList()
        
        self.statusBar.update(self.statusBarText())

    def getCodeChord(self,chordValue):
        return self.codeChords[F"{chordValue}"] if self.codeChords.get(F"{chordValue}") else [] 
    
    def setCodeChord(self,chordValue,strokes):
        if chordValue == None:
            return
        self.codeChords[F"{chordValue}"] = strokes            

    #def autoConn(self,vals):
    #LAMBe

    def clearKeystrokes(self,event):
        verbox("clearing keystrokes")
        values = []
        self.setCodeChord(self.chordSet,values)
        self.updateKeystrokeList()

    def removeKeystroke(self,event):
        verbox("Removing selected keystroke")
        values = self.keystrokeList.GetListValues()
        for stroke in self.keystrokeList.get_indexes():
            values.__delitem__(stroke)
        self.keystrokeList.update(values)
        self.setCodeChord(self.chordSet,values)
        self.updateKeystrokeList()

    def clearKeystrokes(self,event):
        verbox("removing strokes from chord # {self.chordSet}")
        self.setCodeChord(self.chordSet,[""])
        self.updateKeystrokeList()

    def disablePlayback(self, event):
        self.playbackDisabled = not self.playbackDisabled
        self.disablePlaybackBtn.update(button_color=ACTIVE_COLOR if self.playbackDisabled else sg.DEFAULT_BUTTON_COLOR)


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
        self.midiThruState = not self.midiThruState
        verbox("Send recognized keys/chords through MIDI Out." if self.midiThruState else "Silence recognized keys/chords from MIDI Out.")
        self.thruBtn.update(button_color = ACTIVE_COLOR if self.midiThruState else sg.DEFAULT_BUTTON_COLOR)

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
                self.updateKeystrokeList()
                #self.codeChords[self.chordSet] = self.keystrokes
                self.recKeysBtn.update(button_color = sg.DEFAULT_BUTTON_COLOR)
                self.config['autoConn']= self.autoConn
                self.config['codeChords'] = self.codeChords
                sg.user_settings_set_entry('config',self.config)
                sg.user_settings_save(SETTINGS_PATH)
                return
            
        self.recKeysBtn.update(button_color = 'red' if self.recKeysMode else sg.DEFAULT_BUTTON_COLOR)
    
    #update the chord<oops,n.m.>/note associated with a keyboard scan code
    def save(self,values):
        self.config['autoConn'] = self.autoConn
        self.config['midiConnect'] = values
        sg.user_settings_set_entry('config',self.config)
        sg.user_settings_save(SETTINGS_PATH)
        
        sg.user_settings_set_entry('config',self.config)
        print(self.config )
        sg.user_settings_save(SETTINGS_PATH)

    def scanCodeSet(self, sEvent):
        #defunct
        return
        
    def updateKeystrokeList(self):
        self.keystrokeList.update(values = 
                                  self.codeChords[self.chordSet] 
                                  if self.codeChords.get(self.chordSet) else [""])


    def pianoKeysUpdate(self, value: int):
        button_colors = [  ['#666666','#000000'],
        ['#808080','#FFffFF'] ]

        for i in range(12):
            button_color = button_colors[1 if i in self.whiteKeys  else 0][0 if value&2**i else 1]
            self.pianoKeys[i].update(button_color = button_color )

        if value == 0:
            self.chordSet = None
            verbox("No key/chord selected")
            return
        
        s1=chr(19904+value%64)
        s1.encode("utf-8")
        s2=chr(19904+int(value/64)%64)
        s2.encode("utf-8")
        
        verbox(F"Key/Chord {s2}{s1} selected for programming")#{bin(value)[2:]}/

        
        self.chordSet = F"{value}"

        self.updateKeystrokeList()
                     
        #self.config['codeChords'] = self.codeChords
        #sg.user_settings_set_entry('config',self.config)
        #sg.user_settings_save(SETTINGS_PATH)

    def connect(self,values = False):
        #del(self.daemon)
        
        self.connectState = not self.connectState
        if self.connectState == False:
            self.connectBtn.update(text=_("Connect"), button_color=sg.DEFAULT_BUTTON_COLOR)
            return self.disconnect()

        self.daemon = MTKB_Daemon(Client = self)

        if not values:
            #print("no values!",values)
            return
        
        inPort = values.get('midiIn')
        outPort = values.get('midiOut')

        #try try try
        if midi.get_init():
            midi.quit()

        if not midi.get_init():
            midi.init()

        try:
            midiIn = midi.Input(inPort)
            midiIn.poll()
        except:
            verbox(F"midi.Input() I/O error, port is likely in use.")
            return

        
        self.connectBtn.update(text=_("Disconnect"),button_color=ACTIVE_COLOR)
        #self.disconnectBtn.update(disabled=False)
        
        #midiOut = -999
        try:
            midiOut = midi.Output(outPort)
            midiOut.note_off(0,0)
        except:
            verbox("MIDI Output failed, and all you got was this awful error")
            
        
        #and even then
        # if hooked, unhook, it was all a test
        if midi.get_init():
            midi.quit()

        #now, start daemon
        verbox(F"ignition ignitioned.")

        self.daemon.start( (int(inPort),int(outPort)) )


    def disconnect(self):
        if self.daemon:
            verbox("stopping MIDI daemon")
            self.daemon.stop()
    
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

    def __init__(self, Client = None, modulus = 12, offset = 0):
        #debuggery(userInterface)
         
        self.mod = modulus
        self.offset = offset
        self.client = Client
        self.inTheLoop = False
        self.keepAlive = True
        self.midiIn = None
        self.midiOut = None
        self.thread = threading.Thread(target=self.poll)

    def start(self,ioPorts):
        if self.inTheLoop:
            #don't start what you haven't called destruct on
            return
        
        verbox("starting MIDI service.")

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
        verbox("Polling for MIDI note events.")
        verbox(F"In::{midiInPort} Out::{midiOutPort}  initialised :{midi.get_init()}")

    def stop(self):
        self.inTheLoop = self.keepAlive = False
        pygame.quit() 
        pygame.init()
        self.thread._stop()

        
    def poll(self):
        verbox("started MIDI service, polling.")
        keysDown = 0
        notes = []  

        while self.keepAlive:
            #so we know we're inside the keepalive loop
            self.inTheLoop = True

            if self.midiIn.poll():
                
                msg=self.midiIn.read(1) 
                if self.midiOut and self.client.midiThruState:
                    self.midiOut.write(msg)
                msg = msg[0][0]
                
                #verbox(msg)
#                verbox( "˄" if msg[0]==128 else "˅")
#                dir = "up" if msg[0] == 128 else "down"
                note = msg[1]
                note = (note + self.offset) % self.mod
#                note = msg[1] % self.mod

                if msg[0]==128:
                    keysDown-=1
                else:
                    keysDown+=1
                    notes.append(note)
                    
                if keysDown == 0:
                    tot = 0
                    for i in notes:
                        tot += 2**i
                    
                    sTot = F"{tot}"
                    strokes = self.client.getCodeChord(sTot)
#                   verbox(F"chord/key#{tot} ")
                    #verbox(self.client.codeChords)
#                   verbox(strokes)
                    if not self.client.playbackDisabled:
                        if len(strokes)==0:
                            verbox(F"playback {list(strokes)}")
                            for key in strokes:
                                bits = key.split("::")
                                if bits[0] and bits[1]:
                                    ke = keyboard.KeyboardEvent(bits[0],bits[1])
                                    keyboard.play([ke])
                            

                    if self.client.midiMode:
                        #self.client.chordSet = sTot
                        self.client.pianoKeysUpdate(tot)

                    notes = []


if __name__ == "__main__":
    MTKB()
    
    # #it's all over
    # if mtkb.locked is True:
    #     os.remove('./.lock')
