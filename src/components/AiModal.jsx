import { useState, useEffect, useRef } from "react";
import { gsap } from "gsap";
import { FaMicrophone, FaTimes } from "react-icons/fa";
import "./AiModal.scss";

const AiModal = ({ onClose }) => {
  const [messages, setMessages] = useState([
    { text: "Hello 👋 How can I help you?", sender: "ai" },
  ]);
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    gsap.from(".ai-modal", {
      scale: 0.8,
      opacity: 0,
      duration: 0.4,
    });

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.lang = "en-US";

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
      };

      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
    }
  }, []);

  const sendMessage = () => {
    if (!input.trim()) return;

    setMessages([
      ...messages,
      { text: input, sender: "user" },
      { text: "Processing your request...", sender: "ai" },
    ]);

    setInput("");
  };

  const startListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.start();
      setIsListening(true);
    } else {
      alert("Speech recognition not supported in this browser.");
    }
  };

  return (
    <div className="">
      <div className="ai-modal">
        <div className="ai-header">
          <h3>AI Assistant</h3>
          <FaTimes className="close-icon" onClick={onClose} />
        </div>

        <div className="ai-chat">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              {msg.text}
            </div>
          ))}
        </div>

        {isListening && (
          <div className="voice-animation">
            <div></div>
            <div></div>
            <div></div>
            <div></div>
          </div>
        )}

        <div className="ai-input">
          <input
            type="text"
            placeholder="Ask something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <FaMicrophone
            className={`mic-icon ${isListening ? "active" : ""}`}
            onClick={startListening}
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>
    </div>
  );
};

export default AiModal;
