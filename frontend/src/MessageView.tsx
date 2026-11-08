import { Flag } from "./api";
import Highlighted from "./Highlighted";

const HEAD = {
  sms: { icon: "💬", title: "Text message", sub: "Unknown sender · Today" },
  email: { icon: "✉️", title: "Email", sub: "Inbox · Today" },
  voicemail: { icon: "🎙️", title: "Voicemail transcript", sub: "Voicemail · 0:24" },
} as const;

/** Phone-style rendering of a practice message. Flags are only passed in after the user answers. */
export default function MessageView({ channel, text, flags }: { channel: "sms" | "email" | "voicemail"; text: string; flags?: Flag[] }) {
  const h = HEAD[channel];
  return (
    <div className={`phone phone-${channel}`}>
      <div className="phone-head">
        <span aria-hidden className="phone-ico">{h.icon}</span>
        <div><b>{h.title}</b><div className="phone-sub">{h.sub}</div></div>
      </div>
      <div className={`bubble bubble-${channel}`}>
        {flags && flags.length ? <Highlighted text={text} flags={flags} /> : <p className="message-text">{text}</p>}
      </div>
    </div>
  );
}
