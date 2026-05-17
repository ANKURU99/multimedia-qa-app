import React, { useState, useRef } from 'react';
import { Upload, MessageSquare, FileText, Play, Film, AlertCircle } from 'lucide-react';

export default function App() {
  const [fileDetails, setFileDetails] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'summary'
  const [summary, setSummary] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [userQuery, setUserQuery] = useState('');
  const [processingQuery, setProcessingQuery] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Critical React Reference hook to capture and manage the HTML5 media component
  const mediaRef = useRef(null);

  // Programmatic control function to jump directly to target playback timestamps
  const jumpToMediaTimestamp = (seconds) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = seconds;
      mediaRef.current.play().catch(err => console.log("Playback interaction focus required:", err));
    }
  };

  // Parses response text patterns to extract timestamp targets and display interactive buttons
  const renderMessageContent = (text) => {
    // Regex matching timestamp patterns like [MM:SS] or [HH:MM:SS]
    const timestampRegex = /\[(\d{2}):(\d{2})\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = timestampRegex.exec(text)) !== null) {
      // Push text before the timestamp
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      const minutes = parseInt(match[1], 10);
      const seconds = parseInt(match[2], 10);
      const totalSeconds = (minutes * 60) + seconds;

      // Render an active interactive interface button inline
      parts.push(
        <button
          key={match.index}
          onClick={() => jumpToMediaTimestamp(totalSeconds)}
          className="inline-flex items-center mx-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white transition-colors duration-150 shadow-sm"
        >
          <Play size={10} className="mr-1 fill-current" />
          {match[0]}
        </button>
      );
      lastIndex = timestampRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setUploading(true);
    setErrorMessage('');
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Send file to our local FastAPI deployment gateway
      const response = await fetch('http://localhost:8000/upload/file', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('File validation or processing failed.');
      
      const data = await response.json();
      setFileDetails({
        id: data.file_id,
        name: data.filename,
        type: data.type,
        localUrl: URL.createObjectURL(selectedFile) // Creates a safe local blob string for previewing
      });

      // Clear layout and reset configurations
      setChatHistory([{ role: 'assistant', content: `Successfully parsed and indexed ${data.filename}! You can now ask questions or request an automated summary.` }]);
      setSummary('');
    } catch (err) {
      setErrorMessage(err.message || 'Server pipeline communication failure.');
    } finally {
      setUploading(false);
    }
  };

  const handleFetchSummary = async () => {
    if (!fileDetails) return;
    try {
      const response = await fetch(`http://localhost:8000/summary/${fileDetails.id}`);
      const data = await response.json();
      setSummary(data.summary);
    } catch (err) {
      setSummary('Failed to assemble summary data from backend context.');
    }
  };

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!userQuery.trim() || !fileDetails || processingQuery) return;

    const currentQuery = userQuery;
    setUserQuery('');
    setChatHistory(prev => [...prev, { role: 'user', content: currentQuery }]);
    setProcessingQuery(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: fileDetails.id, query: currentQuery }),
      });

      const data = await response.json();
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.answer }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Failed to extract answers from knowledge base.' }]);
    } finally {
      setProcessingQuery(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 font-sans text-slate-100">
      {/* Header Panel */}
      <header className="flex items-center justify-between px-6 py-4 bg-slate-900 border-b border-slate-800 shadow-md">
        <div className="flex items-center space-x-3">
          <Film className="text-emerald-400 animate-pulse" size={24} />
          <h1 className="text-lg font-bold tracking-wide text-slate-100">Multimedia Q&A Engine</h1>
        </div>
      </header>

      {/* Main Workspace Layout Split-Screen Dashboard */}
      <main className="flex flex-1 overflow-hidden p-6 gap-6">
        {/* LEFT WORKSPACE: Ingestion Hub & Active Asset Viewer */}
        <div className="w-1/2 flex flex-col bg-slate-900 rounded-xl border border-slate-800 p-5 shadow-inner">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">Asset Management</h2>
          
          {/* File Upload Interaction Zone */}
          <div className="border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-lg p-6 text-center transition-colors duration-200 cursor-pointer bg-slate-950/40 relative">
            <input type="file" accept=".pdf,.mp3,.mp4" onChange={handleFileUpload} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
            <Upload className="mx-auto text-slate-400 mb-2" size={32} />
            <p className="text-sm font-medium text-slate-300">Drag & Drop or Click to Upload</p>
            <p className="text-xs text-slate-500 mt-1">Supports PDF documents, MP3 Audio, or MP4 Video files</p>
          </div>

          {uploading && (
            <div className="mt-4 p-3 bg-slate-800 rounded-lg flex items-center justify-center space-x-3">
              <div className="w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm font-medium text-emerald-400">Processing media assets into local Vector Store...</p>
            </div>
          )}

          {errorMessage && (
            <div className="mt-4 p-3 bg-red-950/40 border border-red-800 rounded-lg flex items-center space-x-2 text-red-400 text-sm">
              <AlertCircle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Connected HTML5 Dynamic Media / Document Viewer Module */}
          <div className="flex-1 mt-6 bg-slate-950 rounded-lg border border-slate-800 flex flex-col items-center justify-center p-4 relative overflow-auto">
            {fileDetails ? (
              <div className="w-full h-full flex flex-col justify-between">
                <div className="mb-3 px-3 py-1.5 bg-slate-800 rounded text-xs font-mono truncate text-slate-300">
                  Active Asset: {fileDetails.name}
                </div>
                <div className="flex-1 flex items-center justify-center bg-black/30 rounded border border-slate-900 p-2">
                  {fileDetails.type === 'document' ? (
                    <div className="text-center p-6">
                      <FileText size={64} className="mx-auto text-emerald-400 mb-3" />
                      <p className="text-sm font-medium text-slate-300">PDF Document Loaded Systematically</p>
                      <p className="text-xs text-slate-500 mt-1">Vector citations point to structured page modules</p>
                    </div>
                  ) : (
                    <video
                      ref={mediaRef}
                      src={fileDetails.localUrl}
                      controls
                      className="max-h-64 w-full rounded bg-black"
                    />
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500 font-medium">No media uploaded yet. Load an asset to initialize display controls.</p>
            )}
          </div>
        </div>

        {/* RIGHT WORKSPACE: Interactive Dialogue & Document Summary Control Panel */}
        <div className="w-1/2 flex flex-col bg-slate-900 rounded-xl border border-slate-800 shadow-inner overflow-hidden">
          {/* Section Mode Navigation Elements */}
          <div className="flex border-b border-slate-800 bg-slate-950/60 p-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${activeTab === 'chat' ? 'bg-slate-800 text-emerald-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
            >
              <MessageSquare size={16} />
              <span>Chat Assistant</span>
            </button>
            <button
              onClick={() => { setActiveTab('summary'); handleFetchSummary(); }}
              className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors duration-150 ${activeTab === 'summary' ? 'bg-slate-800 text-emerald-400 shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
              disabled={!fileDetails}
            >
              <FileText size={16} />
              <span>Content Summary</span>
            </button>
          </div>

          {/* Dynamic Window Container Section Viewports */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {activeTab === 'chat' ? (
              chatHistory.length > 0 ? (
                chatHistory.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-lg p-3.5 text-sm leading-relaxed shadow-sm ${msg.role === 'user' ? 'bg-emerald-600 text-white font-medium' : 'bg-slate-800 border border-slate-700/60 text-slate-200'}`}>
                      {msg.role === 'assistant' ? renderMessageContent(msg.content) : msg.content}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-sm text-slate-500 py-12">
                  Upload an asset and ask questions to begin analysis.
                </div>
              )
            ) : (
              <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-5 text-sm leading-relaxed text-slate-300 font-normal whitespace-pre-wrap">
                {summary || "Generating abstract context summaries..."}
              </div>
            )}
          </div>

          {/* Bottom Prompt Form Element Frame */}
          {activeTab === 'chat' && (
            <form onSubmit={handleSendChat} className="p-4 bg-slate-950/60 border-t border-slate-800 flex gap-3">
              <input
                type="text"
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
                placeholder={fileDetails ? "Ask a question about your uploaded file..." : "Please upload a file first to activate dialogue functionality"}
                disabled={!fileDetails || processingQuery}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
              <button
                type="submit"
                disabled={!fileDetails || processingQuery}
                className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-800 disabled:text-slate-600 rounded-lg text-sm font-semibold text-white transition-colors shadow-md flex items-center"
              >
                {processingQuery ? 'Searching...' : 'Send'}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
