
// import React, { useEffect } from "react";
// import "./Home.scss";
// import gsap from "gsap";
// import { ScrollTrigger } from "gsap/ScrollTrigger";
// import { Link } from "react-router-dom";

// gsap.registerPlugin(ScrollTrigger);

// const Home = () => {

//   useEffect(() => {

//   let ctx = gsap.context(() => {

//     const sections = document.querySelectorAll(".feature-section");

//     sections.forEach((section) => {

//       const left = section.querySelector(".feature-left");
//       const right = section.querySelector(".feature-right");

//       let tl = gsap.timeline({
//         scrollTrigger: {
//           trigger: section,
//           start: "top 75%",
//           end: "top 25%",
//           scrub: true,
//         }
//       });

//       tl.from(left, {
//         x: -200,
//         opacity: 0,
//       }, "a")

//       tl.from(right, {
//         x: 200,
//         opacity: 0,
//       }, "a");

//     });

//   });

//   return () => ctx.revert();

// }, []);


//   return (
//     <div className="home">

//       {/* HERO SECTION */}
//       <section className="hero">
//         <video autoPlay muted loop className="hero-video">
//           <source src="/4609535-uhd_3840_2160_24fps.mp4" type="video/mp4" />
//         </video>

//         <div className="hero-overlay"></div>

//         <div className="hero-content">
//           <h1>Fleet Sync</h1>
//           <p>India’s Smartest Real-Time Shipment Platform 🚚</p>
//           <div className="hero-buttons">

//             <Link to="/track" className="primary-btn">
//               Track Order
//             </Link>

//             <Link to="/login" className="secondary-btn">
//               Admin Login
//             </Link>

//           </div>

//         </div>
//       </section>

//       {/* FEATURES */}
//       <section className="features">

//         <div className="feature-section">
//           <div className="feature-left">
//             <img src="https://images.unsplash.com/photo-1509395176047-4a66953fd231" alt="" />
//           </div>
//           <div className="feature-right">
//             <h2>Live Vehicle Tracking</h2>
//             <p>Track multiple vehicles in real time with GPS accuracy and smart mapping.</p>
//           </div>
//         </div>

//         <div className="feature-section">
//           <div className="feature-left">
//             <h2>Smart Route Optimization</h2>
//             <p>AI-powered routing for fastest and fuel-efficient deliveries.</p>
//           </div>
//           <div className="feature-right">
//             <img src="https://images.unsplash.com/photo-1556761175-4b46a572b786" alt="" />
//           </div>
//         </div>

//         <div className="feature-section">
//           <div className="feature-left">
//             <img src="https://images.unsplash.com/photo-1551288049-bebda4e38f71" alt="" />
//           </div>
//           <div className="feature-right">
//             <h2>Fleet Analytics Dashboard</h2>
//             <p>Monitor performance, emissions, delivery time and efficiency.</p>
//           </div>
//         </div>

//       </section>

//     </div>
//   );
// };

// export default Home;
// import React, { useEffect, useRef } from "react";
// import "./Home.scss";
// import gsap from "gsap";
// import { ScrollTrigger } from "gsap/ScrollTrigger";

// gsap.registerPlugin(ScrollTrigger);

// const Home = () => {

//   const containerRef = useRef(null);

//   useEffect(() => {

//     let ctx = gsap.context(() => {

//       // HERO TEXT REVEAL
//       gsap.from(".hero-title span", {
//         y: 200,
//         opacity: 0,
//         stagger: 0.1,
//         duration: 1,
//         ease: "power4.out"
//       });

//       // HORIZONTAL SCROLL
//       const sections = gsap.utils.toArray(".panel");

//       gsap.to(sections, {
//         xPercent: -100 * (sections.length - 1),
//         ease: "none",
//         scrollTrigger: {
//           trigger: ".horizontal-section",
//           pin: true,
//           scrub: 1,
//           snap: 1 / (sections.length - 1),
//           end: "+=3000"
//         }
//       });

//     }, containerRef);

//     return () => ctx.revert();

//   }, []);

//   return (
//     <div className="home" ref={containerRef}>

//       {/* HERO */}
//       <section className="hero">
//         <h1 className="hero-title">
//           <span>F</span>
//           <span>L</span>
//           <span>E</span>
//           <span>E</span>
//           <span>T</span>
//           <br />
//           <span>S</span>
//           <span>Y</span>
//           <span>N</span>
//           <span>C</span>
//         </h1>
//         <p className="hero-sub">
//           The Future of Intelligent Logistics
//         </p>
//       </section>

//       {/* HUGE TEXT SCROLL SECTION */}
//       <section className="big-text">
//         <h2>
//           REAL TIME • AI POWERED • NEXT GEN • SMART LOGISTICS
//         </h2>
//       </section>

//       {/* HORIZONTAL SCROLL FEATURES */}
//       <section className="horizontal-section">
//         <div className="panel dark">
//           <h2>Live Tracking</h2>
//         </div>

//         <div className="panel gradient">
//           <h2>AI Route Engine</h2>
//         </div>

//         <div className="panel light">
//           <h2>Fleet Intelligence</h2>
//         </div>
//       </section>

//       {/* FINAL SECTION */}
//       <section className="cta">
//         <h2>Move Smarter. Deliver Faster.</h2>
//         <button>Start Tracking</button>
//       </section>

//     </div>
//   );
// };

// export default Home;

import React, { useEffect } from "react";
import "./Home.scss";
import { Link } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const Home = () => {

  useEffect(() => {

    gsap.from(".hero-left h1", {
      y: 80,
      opacity: 0,
      duration: 1,
      ease: "power4.out"
    });

    gsap.from(".hero-left p", {
      y: 40,
      opacity: 0,
      delay: 0.3
    });

    gsap.from(".dashboard-mockup", {
      x: 100,
      opacity: 0,
      duration: 1,
      delay: 0.5
    });

    gsap.utils.toArray(".feature-section").forEach((el) => {
      gsap.from(el, {
        scrollTrigger: {
          trigger: el,
          start: "top 80%"
        },
        y: 100,
        opacity: 0,
        duration: 1
      });
    });

  }, []);

  return (
    <div className="home">

      {/* NAVBAR */}
      <nav className="navbar">
        <div className="logo">FleetSync</div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#analytics">Analytics</a>
          <Link to="/track" className="nav-btn">Track</Link>
          <Link to="/driver" className="nav-btn">Driver</Link>
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
            and advanced logistics analytics for modern businesses.
          </p>

          <div className="hero-buttons">
            <Link to="/track" className="primary-btn">
              Start Tracking
            </Link>
            <Link to="/login" className="secondary-btn">
              Admin Login
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

        <div className="hero-right">
          <div className="dashboard-mockup">
            <div className="chart"></div>
            <div className="map"></div>
          </div>
        </div>

      </section>

      {/* FEATURES */}
      <section className="feature-section" id="features">
        <h2>Live GPS Tracking</h2>
        <p>
          Monitor vehicle location in real time with smart geofencing,
          route deviation alerts, and dynamic ETA prediction.
        </p>
      </section>

      <section className="feature-section dark">
        <h2>AI Route Optimization</h2>
        <p>
          Our AI engine analyzes traffic, fuel efficiency, and
          weather conditions to determine optimal routes instantly.
        </p>
      </section>

      <section className="feature-section">
        <h2>Advanced Fleet Analytics</h2>
        <p>
          Gain insights into delivery performance, driver behavior,
          emissions tracking, and cost optimization.
        </p>
      </section>

      {/* CTA */}
      <section className="cta">
        <h2>Ready to Upgrade Your Fleet?</h2>
        <Link to="/track" className="primary-btn">
          Get Started Now
        </Link>
      </section>

    </div>
  );
};

export default Home;
