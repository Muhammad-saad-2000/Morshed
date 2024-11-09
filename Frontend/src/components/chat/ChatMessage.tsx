type ChatMessageProps = {
  message: string;
  translation: string;
  accentColor: string;
  name: string;
  summary: string;
  isSelf: boolean;
  hideName?: boolean;
};

export const ChatMessage = ({
  name,
  message,
  translation,
  summary,
  accentColor,
  isSelf,
  hideName,
  isConsecutive, // Indicates if it's part of a consecutive message from the same sender
}: ChatMessageProps) => {
  // Don't render the bubble if the message is empty
  if (!message) return null;

  return (
    <div className={`flex flex-col gap-1 ${hideName || isConsecutive ? "pt-0" : "pt-6"}`}>
      {!hideName && !isConsecutive && (
        <div
          className={`text-${isSelf ? `${accentColor}-400` : `${accentColor}-400`} uppercase text-xs ${isSelf ? "text-right" : ""
            }`}
        >
          {name}
        </div>
      )}
      <div
        className={`p-3 rounded-lg text-${isSelf ? "white" : `${accentColor}-100`} text-sm whitespace-pre-line ${isSelf
          ? "bg-gray-900 self-end"
          : `bg-gray-900`
          } ${isConsecutive ? "mt-1" : "mt-3"}`}
      >
        {message}
        {translation && (
          <div className="mt-1 text-gray-400">
            {translation}
          </div>
        )}
        {summary && (
          <div
            className="mt-1 text-gray-500 italic"
            style={{ fontSize: "0.85rem" }}
          >
            <span style={{ fontWeight: "bold", color: "white", textAlign: "center", display: "block" }}>{"\nالملخص\n"}</span>
            <span style={{ fontWeight: "normal" }}>{summary}</span>
          </div>
        )}
      </div>
    </div>
  );
};
