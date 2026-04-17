import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import SetupScreen from './components/SetupScreen';
import HistoryScreen from './components/HistoryScreen';
import { useAnalysis } from './hooks/useAnalysis';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('setup'); // setup, chat, history
  
  const {
    loading: isLoading,
    error,
    session: analysis,
    messages,
    runAnalysis: analyze,
    runFollowUp: askFollowUp,
    handleUploadFile,
    loadSessionData,
    resetSession: reset,
  } = useAnalysis();

  useEffect(() => {
    // Basic setup check loop
    const userId = localStorage.getItem('supplychainiq_user_id');
    if (!userId) {
      localStorage.setItem('supplychainiq_user_id', 'user_' + Date.now());
    }
  }, []);

  const handleSetupComplete = useCallback(() => {
    setCurrentScreen('chat');
  }, []);

  const handleSelectSessionFromHistory = useCallback((sessionId) => {
    loadSessionData(sessionId);
    setCurrentScreen('chat');
  }, [loadSessionData]);

  const handleSend = useCallback((input, options = {}) => {
    if (!analysis?.session_id || messages.length === 0 || (messages.length === 1 && messages[0].role === 'system')) {
      analyze(input, options);
    } else {
      askFollowUp(input);
    }
  }, [analysis, messages, analyze, askFollowUp]);

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-200 overflow-hidden">
      {/* Background glow effects */}
      <div className="fixed inset-0 pointer-events-none opacity-20">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-600 blur-[120px]" />
        <div className="absolute top-[60%] -right-[10%] w-[50%] h-[50%] rounded-full bg-indigo-600 blur-[120px]" />
      </div>

      <Header 
        onHistoryClick={() => setCurrentScreen('history')}
        onNewChatClick={() => {
          reset();
          setCurrentScreen('chat');
        }}
      />
      
      <div className="flex-1 flex overflow-hidden relative z-10">
        {currentScreen !== 'setup' && (
          <Sidebar analysis={analysis} />
        )}

        <main className={`flex-1 flex flex-col relative ${currentScreen === 'setup' ? 'overflow-auto' : 'overflow-hidden'}`}>
          {currentScreen === 'setup' && (
            <SetupScreen onComplete={handleSetupComplete} />
          )}

          {currentScreen === 'history' && (
            <HistoryScreen onSelectSession={handleSelectSessionFromHistory} />
          )}

          {currentScreen === 'chat' && (
            <ChatInterface
              messages={messages}
              isLoading={isLoading}
              onSend={handleSend}
              onReset={() => {
                reset();
                setCurrentScreen('chat');
              }}
              onFileUpload={handleUploadFile}
              sessionId={analysis?.session_id}
            />
          )}

          {error && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg bg-red-500/90 text-white text-sm shadow-lg z-50"
            >
              {error}
            </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}
