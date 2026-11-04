interface StatusBadgeProps {
  label: string;
  ok: boolean;
}

export default function StatusBadge({ label, ok }: StatusBadgeProps) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.2rem 0.5rem",
        borderRadius: 4,
        fontSize: "0.75rem",
        background: ok ? "rgba(61, 139, 253, 0.2)" : "rgba(200, 80, 80, 0.2)",
        color: ok ? "#3d8bfd" : "#e88",
      }}
    >
      {label}
    </span>
  );
}
