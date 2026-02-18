import wave
import math
import struct

def generate_sine_wave(filename, duration=2, frequency=440, sample_rate=44100):
    n_samples = int(sample_rate * duration)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit PCM)
        wav_file.setframerate(sample_rate)
        
        for i in range(n_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframes(data)
    print(f"Generated {filename}")

if __name__ == "__main__":
    generate_sine_wave("valid_test_audio.wav")
