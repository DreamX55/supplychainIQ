import { useState, useCallback } from 'react';
import { analyzeSupplyChain, sendFollowUp, getSessionDetails, uploadContextFile } from '../utils/api';

export function useAnalysis() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);

  const handleUploadFile = useCallback(async (file) => {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadContextFile(file, session?.session_id);
      if (!session) {
        setSession({ session_id: result.session_id });
      }
      // Add a system message locally to show the file was uploaded
      setMessages(prev => [...prev, { role: 'system', content: `File uploaded: ${result.filename}` }]);
      return result;
    } catch (err) {
      console.error(err);
      setError('Failed to upload file.');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const runAnalysis = useCallback(async (description, options = {}) => {
    setLoading(true);
    setError(null);
    const now = new Date().toISOString();
    setMessages(prev => [...prev, { role: 'user', content: description, timestamp: now }]);
    
    try {
      const result = await analyzeSupplyChain(description, session?.session_id, options);
      setSession(result);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: result.summary, 
        timestamp: new Date().toISOString(),
        analysis: result,
        meta: result.provider_meta || result._meta
      }]);
    } catch (err) {
      console.error(err);
      setError('Analysis failed. Check your API configuration.');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const runFollowUp = useCallback(async (question) => {
    if (!session?.session_id) return;
    
    setLoading(true);
    setError(null);
    const now = new Date().toISOString();
    setMessages(prev => [...prev, { role: 'user', content: question, timestamp: now }]);
    
    try {
      const result = await sendFollowUp(question, session.session_id);
      setSession(prev => ({
        ...prev,
        follow_up_suggestions: result.follow_up_suggestions
      }));
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: result.message, 
        timestamp: new Date().toISOString(),
        followUp: result,
        meta: result.provider_meta || result._meta
      }]);
    } catch (err) {
      console.error(err);
      setError('Follow-up failed.');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const loadSessionData = useCallback(async (sessionId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSessionDetails(sessionId);

      setSession({
        session_id: data.session_id,
        risk_nodes: data.analysis?.risk_nodes || [],
        overall_risk_level: data.analysis?.overall_risk_level || 'Medium',
        summary: data.analysis?.summary || data.analysis_summary || '',
        entities_detected: data.entities || {},
        follow_up_suggestions: []
      });

      // Sort then rehydrate: assistant messages are stored as JSON-encoded
      // analysis/followup payloads — parse them so each replayed turn renders
      // its rich Risk Brief / follow-up card instead of a raw JSON blob.
      const sortedHistory = (data.history || []).sort(
        (a, b) => new Date(a.created_at) - new Date(b.created_at)
      );

      const rehydrated = sortedHistory.map((m) => {
        const base = { role: m.role, content: m.content, timestamp: m.created_at };
        if (m.role !== 'assistant') return base;

        const raw = (m.content || '').trim();
        if (!raw || (raw[0] !== '{' && raw[0] !== '[')) return base;

        let parsed;
        try {
          parsed = JSON.parse(raw);
        } catch {
          return base; // legacy / unparseable — leave as-is
        }
        if (!parsed || typeof parsed !== 'object') return base;

        const meta = parsed._meta || undefined;

        // Analysis shape: has risk_nodes
        if (Array.isArray(parsed.risk_nodes)) {
          return {
            ...base,
            content: parsed.summary || base.content,
            analysis: parsed,
            meta,
          };
        }

        // Follow-up shape: has message
        if (typeof parsed.message === 'string') {
          return {
            ...base,
            content: parsed.message,
            followUp: parsed,
            meta,
          };
        }

        return base;
      });

      setMessages(rehydrated);
    } catch (err) {
      console.error(err);
      setError('Failed to load session details.');
    } finally {
      setLoading(false);
    }
  }, []);

  const resetSession = useCallback(() => {
    setSession(null);
    setMessages([]);
    setError(null);
  }, []);

  return {
    loading,
    error,
    session,
    messages,
    runAnalysis,
    runFollowUp,
    handleUploadFile,
    loadSessionData,
    resetSession
  };
}
