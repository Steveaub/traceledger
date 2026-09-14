# Voice input and read-aloud

Click Speak question to dictate, review the text, then click Find evidence. Stop microphone ends dictation. No question is submitted automatically. Listen speaks the displayed answer and citation numbers; The same button changes to Stop and cancels playback. New questions cancel previous speech. Text entry remains available.

Recognition uses the browser Web Speech API and may send audio to the browser provider. TraceLedger does not record or store audio. Browser support and microphone permissions vary; when unavailable use Chrome or focus the question box and press Windows + H. Read-aloud requires an installed local English system voice and does not fall back to a remote voice.

This adds speech input/output to text RAG; it does not add image, video, or audio-document retrieval. Retrieval benchmarks are unchanged. Voice behavior is tested with mocked browser APIs; actual microphone transcription and audible playback require testing on the user's device.
