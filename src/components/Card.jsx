import React from 'react';
import { useFleetStats } from '../context/FleetStatsContext';

const Card = () => {
    const { stats } = useFleetStats();
    return (
        <div className="cards">
            <div className='cd'>
                <div className="card">
                    <h4>Route Efficiency</h4>
                    <p>{stats.routeEfficiency}%</p>
                </div>
                <div className="card">
                    <h4>Total Fleet</h4>
                    <p>{stats.totalFleet} Vehicles</p>
                </div>
            </div>
            <div className='cd'>
                <div className="card">
                    <h4>Total Distance</h4>
                    <p>{stats.totalDistance.toLocaleString()} km</p>
                </div>
                <div className="card">
                    <h4>Total CO₂</h4>
                    <p>{stats.totalCO2.toLocaleString()} kg</p>
                </div>
            </div>
        </div>
    );
};

export default Card;
