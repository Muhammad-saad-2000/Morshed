import { ChatMessageType, ChatTile } from "@/components/chat/ChatTile";
import {
  TrackReferenceOrPlaceholder,
  useChat,
  useLocalParticipant,
  useTrackTranscription,
} from "@livekit/components-react";
import {
  LocalParticipant,
  Participant,
  Track,
  TranscriptionSegment,
} from "livekit-client";
import { useEffect, useState } from "react";
import translate from 'google-translate-api-x';
import Groq from 'groq-sdk';
import OpenAI from 'openai';

import { franc, francAll } from 'franc'
import { has, set } from "lodash";


export function TranscriptionTile({
  agentAudioTrack,
  accentColor,
  clientName,
  address,
  emergency,
  setLanguage,
  setClientName,
  setAddress,
  setEmergency,
}: {
  agentAudioTrack: TrackReferenceOrPlaceholder;
  accentColor: string;
  clientName: string;
  address: string;
  emergency: string;
  setLanguage: (lang: string) => void;
  setClientName: (name: string) => void;
  setAddress: (address: string) => void;
  setEmergency: (emergency: string) => void;
}) {
  const agentMessages = useTrackTranscription(agentAudioTrack);
  const localParticipant = useLocalParticipant();
  const localMessages = useTrackTranscription({
    publication: localParticipant.microphoneTrack,
    source: Track.Source.Microphone,
    participant: localParticipant.localParticipant,
  });


  const [transcripts, setTranscripts] = useState<Map<string, ChatMessageType>>(
    new Map()
  );
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const { chatMessages, send: sendChat } = useChat();
  const [nameSet, setNameSet] = useState(false);

  useEffect(() => {
    const updateTranscripts = async () => {
      for (const s of agentMessages.segments) {
        transcripts.set(
          s.id,
          await segmentToChatMessage(
            s,
            transcripts.get(s.id),
            agentAudioTrack.participant,
            messages,
            clientName, address, emergency,
            setLanguage,
            setClientName,
            setAddress,
            setEmergency,
          )
        );
      }
      for (const s of localMessages.segments) {
        transcripts.set(
          s.id,
          await segmentToChatMessage(
            s,
            transcripts.get(s.id),
            localParticipant.localParticipant,
            messages,
            clientName, address, emergency,
            setLanguage,
            setClientName,
            setAddress,
            setEmergency,
          )
        );
      }

      const allMessages = Array.from(transcripts.values());
      for (const msg of chatMessages) {
        const isAgent =
          msg.from?.identity === agentAudioTrack.participant?.identity;
        const isSelf =
          msg.from?.identity === localParticipant.localParticipant.identity;
        let name = msg.from?.name;
        if (!name) {
          if (isAgent) {
            name = "Agent";
          } else if (isSelf) {
            name = "You";
          } else {
            name = "Unknown";
          }
        }


        allMessages.push({
          name,
          message: msg.message,
          translation: "",
          timestamp: msg.timestamp,
          isSelf: isSelf,
        });
      }



      allMessages.sort((a, b) => a.timestamp - b.timestamp);
      setMessages(allMessages);
    };

    updateTranscripts();
  }, [
    transcripts,
    chatMessages,
    localParticipant.localParticipant,
    agentAudioTrack.participant,
    agentMessages.segments,
    localMessages.segments,
    clientName,
    address,
    emergency,
  ]);

  return (
    <ChatTile messages={messages} accentColor={accentColor} onSend={sendChat} />
  );
}

async function segmentToChatMessage(
  s: TranscriptionSegment,
  existingMessage: ChatMessageType | undefined,
  participant: Participant,
  messages: ChatMessageType[],
  clientName: string,
  address: string,
  emergency: string,
  setLanguage: (lang: string) => void,
  setClientName: (name: string) => void,
  setAddress: (address: string) => void,
  setEmergency: (emergency: string) => void
): Promise<ChatMessageType> {
  let translation = '';

  let summary = '';

  const msg: ChatMessageType = {
    message: s.final ? s.text : `${s.text} ...`,
    name: participant instanceof LocalParticipant ? "You" : "Allam",
    translation: translation,
    summary: summary,
    isSelf: participant instanceof LocalParticipant,
    timestamp: existingMessage?.timestamp ?? Date.now(),
  };

  return msg;
}