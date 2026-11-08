import { FLAG_LABELS, Flag } from "./api";

/** Renders text with red-flag spans marked. Marks use underline + a text label, not color alone. */
export default function Highlighted({ text, flags }: { text: string; flags: Flag[] }) {
  const parts: JSX.Element[] = [];
  let pos = 0;
  [...flags].sort((a, b) => a.start - b.start).forEach((f, i) => {
    if (f.start < pos) return;
    parts.push(<span key={`t${i}`}>{text.slice(pos, f.start)}</span>);
    parts.push(
      <mark key={`m${i}`} className={`flag flag-${f.type}`} title={FLAG_LABELS[f.type] ?? f.type}>
        {text.slice(f.start, f.end)}
        <sup className="flag-tag">{FLAG_LABELS[f.type] ?? f.type}</sup>
      </mark>
    );
    pos = f.end;
  });
  parts.push(<span key="end">{text.slice(pos)}</span>);
  return <p className="message-text">{parts}</p>;
}
