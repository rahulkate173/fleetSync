
import React, { useEffect, useRef } from "react";
import "./Home.scss";
import { Link } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const Home = () => {
  const containerRef = useRef();

useEffect(() => {

  const section = document.querySelector(".Section2");
  if (!section) return;

  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: section,
      start: "top 70%",
      end: "+=1000",
      scrub: 1,
    }
  });

  tl.from(".sec2Top", {
    y: 60,
    opacity: 0
  });

  // FIRST
  tl.from("#first .feature-left", {
    x: -150,
    opacity: 0
  }, "a");

  tl.from("#first .feature-right", {
    x: 150,
    opacity: 0
  }, "a");

  // SECOND
  tl.from("#second .feature-left", {
    x: -150,
    opacity: 0
  }, "b");

  tl.from("#second .feature-right", {
    x: 150,
    opacity: 0
  }, "b");

  // THIRD
  tl.from("#third .feature-left", {
    x: -150,
    opacity: 0
  }, "c");

  tl.from("#third .feature-right", {
    x: 150,
    opacity: 0
  }, "c");

  // FOURTH
  tl.from("#fourth .feature-left", {
    x: -150,
    opacity: 0
  }, "d");

  tl.from("#fourth .feature-right", {
    x: 150,
    opacity: 0
  }, "d");

  return () => {
    tl.scrollTrigger?.kill();
    tl.kill();
  };

}, []);


  return (
    <div className="home" ref={containerRef}>

      {/* NAVBAR */}
      <nav className="navbar">
        <div className="logo">FleetSync</div>
        <div className="nav-links">
          <a href="#features" className="nav-btn">Features</a>
          <Link to="/track" className="nav-btn">Track</Link>
        </div>
      </nav>

      {/* HERO */}
      <section className="hero">
        <div className="hero-left">
          <h1>
            Smart Fleet <br /> Intelligence Platform
          </h1>
          <p>
            Real-time GPS tracking, AI-powered route optimization,
            and advanced logistics analytics.
          </p>

          <div className="hero-buttons">
            <Link to="/user/order" className="primary-btn">
              user
            </Link>
            <Link to="/login" className="secondary-btn">
              Admin Login
            </Link>
             <Link to="/driver" className="secondary-btn">
              Driver Login
            </Link>
          </div>

          <div className="hero-stats">
            <div>
              <h3>120K+</h3>
              <span>Deliveries</span>
            </div>
            <div>
              <h3>98%</h3>
              <span>Accuracy</span>
            </div>
            <div>
              <h3>500+</h3>
              <span>Vehicles</span>
            </div>
          </div>
        </div>

          <div className="videoDiv">
            {/* <video  autoPlay muted loop src="/4609535-uhd_3840_2160_24fps.mp4"></video> */}
          <img className="imgworld" src="/Frame 1.png" alt="" />
          </div>
        {/* </div> */}
      </section>

      {/* FEATURES SECTION */}
     <div className="curve-divider"></div>


      <section className="Section2" id="features">

        <div className="sec2Top">
          <h2>Powerful Fleet Features</h2>
          <p>Smart tools designed for modern logistics operations</p>
        </div>

        <div className="feature-wrapper">

          <div className="feature-section" id="first">
            <div className="feature-left">
              <img src="https://images.unsplash.com/photo-1509395176047-4a66953fd231" alt="" />
            </div>
            <div className="feature-right">
              <h3>Live Vehicle Tracking</h3>
              <p>Track vehicles in real time with GPS precision.</p>
            </div>
          </div>

          <div className="feature-section" id="second">
            <div className="feature-left">
              <h3>Smart Route Optimization</h3>
              <p>AI-powered fastest and fuel-efficient routing.</p>
            </div>
            <div className="feature-right">
              <img src="https://images.unsplash.com/photo-1556761175-4b46a572b786" alt="" />
            </div>
          </div>

          <div className="feature-section" id="third">
            <div className="feature-left">
              <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71" alt="" />
            </div>
            <div className="feature-right">
              <h3>Fleet Analytics</h3>
              <p>Performance insights, driver behavior & cost analytics.</p>
            </div>
          </div>

          <div className="feature-section" id="fourth">
            <div className="feature-left">
              <h3>Smart Alerts & Geofencing</h3>
              <p>Instant notifications for route deviations and delays.</p>
            </div>
            <div className="feature-right">
              <img src="https://images.unsplash.com/photo-1492724441997-5dc865305da7" alt="" />
            </div>
          </div>

        </div>

      </section>

    </div>
  );
};

export default Home;
