import speech_recognition as sr

print("--- DAFTAR MICROPHONE ---")
mics = sr.Microphone.list_microphone_names()

for index, name in enumerate(mics):
    print(f"Index {index}: {name}")

print("\n-------------------------")
print("Cari yang ada tulisan 'USB PnP', 'Realtek', atau nama Headset kamu.")