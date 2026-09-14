/* Voice is an optional browser adapter; the evidence pipeline still receives text. */
(() => {
  const byId = id => document.getElementById(id);
  const mic = byId('microphone'), question = byId('question');
  const voiceStatus = byId('voice-status'), speechStatus = byId('speech-status');
  const read = byId('read-aloud');
  const microphoneIcon = mic.innerHTML;
  let speaking = false;
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const synthesis = window.speechSynthesis;
  let recognition = null, listening = false, answer = '', speechVersion = 0;

  function stopReading() {
    speechVersion++;
    if (synthesis) synthesis.cancel();
    read.disabled = !answer || !synthesis;
    speaking = false;
    read.textContent = 'Listen';
    read.setAttribute('aria-pressed', 'false');
    speechStatus.textContent = '';
  }

  function stopListening() {
    if (recognition) {
      const old = recognition;
      recognition = null; // Ignore late results after submitting or leaving.
      old.abort();
    }
    listening = false;
    question.readOnly = false;
    mic.innerHTML = microphoneIcon;
    mic.setAttribute('aria-label', 'Speak your question');
    mic.title = 'Speak your question';
    mic.setAttribute('aria-pressed', 'false');
  }

  if (!Recognition) {
    mic.disabled = true;
    voiceStatus.textContent = 'Voice input is unavailable in this browser. Try Chrome, or click the text box and use Windows + H.';
  }
  if (!synthesis || !window.SpeechSynthesisUtterance) {
    read.disabled = true;
    speechStatus.textContent = 'Read aloud is unavailable in this browser.';
  }

  mic.addEventListener('click', () => {
    if (listening) {
      recognition.stop(); // Final transcript may arrive before onend.
      return;
    }
    stopReading();
    const session = new Recognition();
    recognition = session;
    const prefix = question.value.trim();
    session.lang = 'en-US';
    session.continuous = false;
    session.interimResults = true;
    listening = true;
    question.readOnly = true;
    mic.textContent = '■';
    mic.setAttribute('aria-label', 'Stop microphone');
    mic.title = 'Stop microphone';
    mic.setAttribute('aria-pressed', 'true');
    voiceStatus.textContent = 'Listening… Speak your question.';
    session.onresult = event => {
      if (recognition !== session) return;
      const transcript = Array.from(event.results, r => r[0].transcript).join(' ');
      const combined = [prefix, transcript].filter(Boolean).join(' ');
      question.value = combined.slice(0, 1000);
      voiceStatus.textContent = combined.length > 1000
        ? 'Question limited to 1,000 characters. Review before submitting.'
        : 'Transcript ready to review. Click Find evidence when you’re ready.';
    };
    session.onerror = event => {
      if (recognition !== session) return;
      const messages = {
        'not-allowed': 'Microphone access was denied. Allow it in browser settings, or type your question.',
        'service-not-allowed': 'This browser cannot use its speech service. Try Chrome or Windows + H.',
        'audio-capture': 'No microphone is available. Check your microphone connection.',
        'no-speech': 'No speech detected. Try again when you’re ready.',
        'network': 'The browser speech service could not connect. Try again or use Windows + H.',
        'aborted': 'Microphone stopped.'
      };
      voiceStatus.textContent = messages[event.error] || 'Voice input failed. You can still type your question.';
    };
    session.onend = () => {
      if (recognition !== session) return;
      recognition = null;
      listening = false;
      question.readOnly = false;
      mic.innerHTML = microphoneIcon;
    mic.setAttribute('aria-label', 'Speak your question');
    mic.title = 'Speak your question';
      mic.setAttribute('aria-pressed', 'false');
      if (voiceStatus.textContent.startsWith('Listening')) voiceStatus.textContent = 'Microphone stopped. Review your question.';
    };
    try { session.start(); }
    catch (_) { stopListening(); voiceStatus.textContent = 'Could not start voice input. Try Chrome or Windows + H.'; }
  });

  read.addEventListener('click', () => {
    if (speaking) { stopReading(); return; }
    stopListening();
    stopReading();
    if (!answer || !synthesis) return;
    const version = speechVersion;
    // Short utterances avoid long-answer playback stalls. Retain citation numbers.
    const spoken = answer.replace(/\[(\d+)\]/g, ', source $1.');
    const segments = spoken.match(/[^.!?\n]+[.!?]?/g) || [spoken];
    const queue = segments.flatMap(s => s.match(/.{1,220}(?:\s|$)|.{1,220}/g) || []);
    const voices = synthesis.getVoices();
    const voice = voices.find(v => v.localService && v.lang.startsWith('en'));
    if (!voice) {
      speechStatus.textContent = 'No local English voice is available. Enable an English voice in your system settings.';
      return;
    }
    read.disabled = false;
    speaking = true;
    read.textContent = 'Stop';
    read.setAttribute('aria-pressed', 'true');
    speechStatus.textContent = 'Reading the displayed answer…';
    function next() {
      if (version !== speechVersion) return;
      const text = queue.shift();
      if (!text) { stopReading(); return; }
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.voice = voice;
      utterance.lang = voice.lang;
      utterance.onend = next;
      utterance.onerror = () => {
        if (version !== speechVersion) return;
        stopReading();
        speechStatus.textContent = 'Playback failed. Try Read aloud again.';
      };
      synthesis.speak(utterance);
    }
    next();
  });

  window.addEventListener('pagehide', () => { stopListening(); stopReading(); });
  document.querySelectorAll('.scenario').forEach(button => button.addEventListener('click', stopListening));
  window.atlasVoice = {
    reset() { stopListening(); answer = ''; stopReading(); },
    stop() { stopListening(); stopReading(); },
    setAnswer(text) { stopReading(); answer = text; read.disabled = !text || !synthesis; }
  };
})();
