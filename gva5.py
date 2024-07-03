# Google Gemini-Powered Multilingual Voice Assistant
# Multi-language conversation
# Tested and working on Windows 
# By TechMakerAI on YouTube
#  
import google.generativeai as genai
import speech_recognition as sr
from datetime import date
from gtts import gTTS
from io import BytesIO
from pygame import mixer 
import threading
import queue
import time
 
mixer.init()
mixer.set_num_channels(1)
voice = mixer.Channel(0)

#os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# set Google Gemini API key as a system environment variable or add it here
# genai.configure(api_key="Your-Google-API-key")

# model of Google Gemini API
model = genai.GenerativeModel('gemini-pro',
    generation_config=genai.GenerationConfig(
        candidate_count=1,
        top_p = 0.7,
        top_k = 4,
        max_output_tokens=60, # 100 tokens correspond to roughly 60-80 words.
        temperature=0.7,
    ))

# start the chat model 
chat = model.start_chat(history=[])


today = str(date.today())

# Initialize the counters  
numtext = 0 
numtts = 0 
numaudio = 0

# thread 1 for text generation 
def chatfun(request, text_queue, llm_done):
    global numtext, chat
    
    response = chat.send_message(request, stream=True)
 
    # response.resolve() # waits for the completion of streaming response. 
         
    for chunk in response:
        if chunk.candidates[0].content.parts:
            print(chunk.candidates[0].content.parts[0].text, end='') #, flush=True) 
            text_queue.put(chunk.text.replace("*", ""))
            time.sleep(0.2)
            numtext += 1  
            
    append2log(f"AI: {response.candidates[0].content.parts[0].text } \n")
    
    llm_done.set()  # Signal completion after the loop

    
# convert "text" to audio file and play back 
def speak_text(text):
    global slang
    
    if slang == "en-EN":
        tklang = "en"
    else:
        tklang = 'zh-CN'
        
    mp3file = BytesIO()
    tts = gTTS(text, lang = tklang, tld = 'us') 
    tts.write_to_fp(mp3file)

    mp3file.seek(0)
 
    sound1  = mixer.Sound(mp3file) 
 
    voice.play( sound1 )
    
    print("AI: ", text)    
    
    while voice.get_busy():
        time.sleep(0.01)
        
    # close file to avoid memory leak 
    mp3file = None
  
# thread 2 for tts    
def text2speech(text_queue, tts_done, llm_done, audio_queue, stop_event):

    global numtext, numtts, slang
    
    numshort = 0
 
    if slang == "en-EN":
        tklang = "en"
    else:
        tklang = 'zh-CN'
        
    time.sleep(1.0)  
    
    while not stop_event.is_set():  # Keep running until stop_event is set
        
        if not text_queue.empty():
            text = text_queue.get(timeout = 0.5)  # Wait for 2 second for an item
             
            if len(text) > 1:
 
                mp3file1 = BytesIO()
                tts = gTTS(text, lang = tklang, tld = 'us') 
                tts.write_to_fp(mp3file1)
        
                audio_queue.put(mp3file1)
                numtts += 1  
                text_queue.task_done()
            else:
                print("skipping text: ", text)
                numshort += 1 
                text_queue.task_done()
 
        if llm_done.is_set() and numtts + numshort == numtext: 
            
            time.sleep(0.2) 
            tts_done.set()
            mp3file1 = None
            #print("break from the text queue" )

            break 
 

# thread 3 for audio playback 
def play_audio(audio_queue,tts_done, stop_event):
 
    global numtts, numaudio 
        
    #print("start play_audio()")
    while not stop_event.is_set():  # Keep running until stop_event is set
 
        mp3audio1 = BytesIO() 
        mp3audio1 = audio_queue.get()  

        mp3audio1.seek(0)  
        sound1  = mixer.Sound(mp3audio1) 
 
        voice.play( sound1 )
 
        numaudio += 1   
        
        #print("Numaudio: ", numaudio )  
 
        audio_queue.task_done() 
        
        while voice.get_busy():
            time.sleep(0.01)
 
        #print("\n numtts, numaudio : ", numtts , numaudio)
        
        if tts_done.is_set() and numtts  == numaudio: 
            mp3audio1 = None
            #print("\n no more audio/text data, breaking from audio thread")
            break  # Exit loop      
 
# save conversation to a log file 
def append2log(text):
    global today
    fname = 'chatlog-' + today + '.txt'
    with open(fname, "a", encoding='utf-8') as f:
        f.write(text + "\n")
        f.close 
      
# define default language to work with the AI model 
slang = "en-EN"

# Main function  
def main():
    global today, slang, chat, model, numtext, numtts, numaudio, messages
    
    rec = sr.Recognizer()
    mic = sr.Microphone()
    rec.dynamic_energy_threshold=False
    rec.energy_threshold = 400    
  
    sleeping = True 
    # while loop for conversation 
    while True:     
        
        with mic as source:            
            rec.adjust_for_ambient_noise(source, duration= 1)

            print("Listening ...")
            
            try: 
                audio = rec.listen(source, timeout = 20, phrase_time_limit = 30)
                text = rec.recognize_google(audio, language=slang)
 
                # AI is in sleeping mode
                if sleeping == True:
                    # User can start the conversation with the wake word "Jack"
                    # This word can be chagned below. 
                    if "jack" in text.lower() and slang == "en-EN":
                        request = text.lower().split("jack")[1]
                        
                        sleeping = False
                        # AI is awake now, 
                        # start a new conversation 

                        chat = model.start_chat(history=[])

                        append2log(f"_"*40)                    
                        today = str(date.today())  
                        
                        messages = []                      
                     
                        # if the user's question is none or too short, skip 
                        if len(request) < 2:
 
                            speak_text("Hi, there, how can I help?")
                            append2log(f"AI: Hi, there, how can I help? \n")
                            continue                      
                        elif "speak chinese with you" in request.lower():
                            slang = "zh-CN"                           
                            print("Now speak chinese ...")
                            
                        elif "ask you something in chinese" in request.lower():
                            slang = "zh-CN"
                            print("Now speak Chinese ...")
                        
                    # user can start the conversation with the Chinese wake word too 
                    elif "杰克" in text and slang == "zh-CN":
                        request = text[2:]  
                        
                        sleeping = False
                        # AI is awake now, 
                        # start a new conversation 
                        chat = model.start_chat(history=[])
                        append2log(f"_"*40)                     
                        today = str(date.today()) 
                        
                        messages = []  
                        # if the user's question is none or too short, skip 
                        if len(request) < 2:
                            speak_text("你好，请问有什么可以帮忙的吗？")
                            append2log(f"AI: 你好，请问有什么可以帮忙的吗？ \n")
                            continue   
                        
                        if "英文和你聊天" in request: 
                            slang = "en-EN"
                            print("Now speak English ...")
                            
                    # if user did not say the wake word, nothing will happen 
                    else:
                        continue
                      
                # AI is awake         
                else: 
                    
                    request = text.lower()

                    if "that's all" in request:
                                               
                        append2log(f"You: {request}\n")
                        
                        speak_text("Bye now")
                        
                        append2log(f"AI: Bye now. \n")                        
 
                        sleeping = True
                        # AI goes back to speeling mode
                        continue
                    
                    if "jack" in request:
                        request = request.split("jack")[1]
                        
                    if "speak with you in chinese" in request.lower():
                        slang = "zh-CN"
                        print("Now speak Chinese ...")
                        
                    if "ask you something in chinese" in request.lower():
                        slang = "zh-CN"
                        print("Now speak Chinese ...")
                        
                    if "英文和你聊天" in request: 
                        slang = "en-EN"
                        print("Now speak English ...")
                        
                # process user's request (question)
                append2log(f"You: {request}\n ")

                print(f"You: {request}\n AI: ", end='')
                
                # Initialize the counters before each reply from AI 
                numtext = 0 
                numtts = 0 
                numaudio = 0
                
                # Define text and audio queues for data storage 
                text_queue = queue.Queue()
                audio_queue = queue.Queue()
                
                # Define events
                llm_done = threading.Event()                
                tts_done = threading.Event() 
                stop_event = threading.Event()                
     
                # Thread 1 for handleing the LLM responses 
                llm_thread = threading.Thread(target=chatfun, args=(request, text_queue,llm_done,))

                # Thread 2 for text-to-speech 
                tts_thread = threading.Thread(target=text2speech, args=(text_queue,tts_done,llm_done, audio_queue, stop_event,))
                
                # Thread 3 for audio playback 
                play_thread = threading.Thread(target=play_audio, args=(audio_queue,tts_done, stop_event,))
 
                llm_thread.start()
                tts_thread.start()
                play_thread.start()
                
                # wait for LLM to finish responding
                llm_done.wait()

                llm_thread.join() 
                
                tts_done.wait()
                
                audio_queue.join()
 
                stop_event.set()  
                tts_thread.join()
 
                play_thread.join()  
 
                print('\n')
 
            except Exception as e:
                continue 
 
if __name__ == "__main__":
    main()








