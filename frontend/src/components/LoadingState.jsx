import React from "react";

export default function LoadingState({ message = "Loading available products..." }) {
  return (
    <div className="state-container">
      <div className="spinner" role="status" aria-label="Loading"></div>
      <h3 className="state-title">Please Wait</h3>
      <p className="state-text">{message}</p>
    </div>
  );
}
