import { useState } from "react";

export default function PendingForm({ message, children }) {
  const [submitted, setSubmitted] = useState(false);
  return <form className="login-form" action="#" method="post" onSubmit={(event) => {
    event.preventDefault();
    setSubmitted(true);
  }}>
    {children}
    <p className="form-feedback" role="status">{submitted ? message : ""}</p>
  </form>;
}
