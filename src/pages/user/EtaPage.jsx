import UserSidebar from "./UserSidebar";
import "./EtaPage.scss";

const EtaPage = () => {
  return (
    <div className="eta-layout">
      <UserSidebar />

      <div className="eta-content">
        <div className="eta-card">
          <h2>Enter Referral</h2>
          <input placeholder="Referral code" />

          <h3>Captcha</h3>
          <input placeholder="Enter captcha" />

          <button className="eta-btn">
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
};

export default EtaPage;