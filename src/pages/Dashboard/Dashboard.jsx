import "./Dashboard.scss";
import axios from "axios";
import FleetHtmlMap from "../../components/FleetHtmlMap";
import React, { useState, useEffect } from "react";
import Side from "../../components/Side";
import Header from "../../components/Header";
import Sidebar from "../../components/Sidebar";
import Analysis from "../Analysis/Analysis";
import Chart from "../../components/Chart";
import { useShipmentData } from "../../context/ShipmentDataContext";
import Card from "../../components/Card";

const Dashboard = () => {
  const shipmentData = useShipmentData();
  const [active, setActive] = useState(0);
  const [total, setTotal] = useState(0);
  
  // 🚀 NEW: Chat state
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Fleet AI ready! Ask about trucks, locations, delays, CO2...' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get("https://server-production-cd13.up.railway.app/dashboard/summary");
        const data = res.data;
        setActive(data.fleet_status.delayed || 0);
        setTotal(data.fleet_status.total || 0);
      } catch (err) {
        console.error("Error fetching dashboard summary:", err);
      }
    };

    fetchData();
  }, []);

  // 🚀 NEW: Send chat message to FastAPI /chat/admin
  const sendChatMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = { role: 'user', content: chatInput };
    setChatMessages(messages => [...messages, userMessage]);
    setChatLoading(true);
    setChatInput('');

    try {
      const response = await axios.post("https://server-production-cd13.up.railway.app/chat/admin", chatInput, {
        headers: { 'Content-Type': 'application/json' }
      });
      
      const aiResponse = { 
        role: 'assistant', 
        content: response.data.answer || 'Processing fleet data...' 
      };
      setChatMessages(messages => [...messages, aiResponse]);
    } catch (error) {
      const errorMsg = { 
        role: 'assistant', 
        content: 'Chat service busy. Try: "How many trucks active?"' 
      };
      setChatMessages(messages => [...messages, errorMsg]);
    }
    
    setChatLoading(false);
  };

  return (
    <div className="dashboard">
      <Sidebar />
      <div className="main">
        <div className="content">
          <div className="top-section">
            <div className="map-card">
              <h3>Live Vehicle Tracking</h3>
              <FleetHtmlMap />
            </div>
          </div>

          <div className="middle-section">
            <div className="card shipment-details">
              <h2>Fleet Status</h2>
              <div className="fleet-count">
                <span className="active">{total-active}</span>
                <span className="divider">/</span>
                <span className="total">{total}</span>
                <p>Fleets Active</p>
              </div>
            </div>

            <div className="card truck-capacity">
              <h3>Current Truck Capacity</h3>
              <div className="truck-box">
                <div className="capacity-bar">
                  <div className="fill"></div>
                </div>
                <p>86%</p>
              </div>
            </div>
          </div>

          <div className="bottom-section">
            <div className="card trends">
              <Chart shipmentData={shipmentData} />
            </div>

            <div className="card efficiency">
              <Card />
            </div>

            {/* 🚀 REAL CHAT - Replaces AiModal - SAME UI CONTAINER */}
            <div className="card chat">
              <div className="chat-header">
                <h3>Fleet AI Assistant</h3>
                <span className="live-indicator">
                  {total} trucks live
                </span>
              </div>
              
              {/* Chat Messages */}
              <div className="chat-messages">
                {chatMessages.map((msg, index) => (
                  <div key={index} className={`chat-message ${msg.role}`}>
                    <div className="message-bubble">
                      {msg.content}
                    </div>
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-message assistant">
                    <div className="message-bubble">AI thinking...</div>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <div className="chat-input">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                  placeholder="Ask about trucks, delays, routes, CO2..."
                  disabled={chatLoading}
                />
                <button
                  onClick={sendChatMessage}
                  disabled={chatLoading || !chatInput.trim()}
                >
                  {chatLoading ? '...' : 'Send'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
