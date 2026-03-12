import { useState, useRef, useCallback, useEffect } from 'react'
import { Mic, Square, Loader2, Volume2, AlertCircle } from 'lucide-react'

const API_BASE = '/api/v1'

interface VoiceRecorderProps {
  onTranscription: (text: string, duration: number) => void
  onError?: (error: string) => void
  disabled?: boolean
  sessionId?: string // Optional: for interview mode
}

type RecordingState = 'idle' | 'recording' | 'processing'

export default function VoiceRecorder({
  onTranscription,
  onError,
  disabled = false,
  sessionId,
}: VoiceRecorderProps) {
  const [state, setState] = useState<RecordingState>('idle')
  const [duration, setDuration] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(0)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)

    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
    setAudioLevel(average / 255) // Normalize to 0-1

    animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
  }, [])

  const startRecording = useCallback(async () => {
    try {
      setError(null)

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      })

      streamRef.current = stream

      // Set up audio analysis for visualization
      const audioContext = new AudioContext()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      // Determine best supported format
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
      ]
      let selectedMimeType = ''
      for (const type of mimeTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
          selectedMimeType = type
          break
        }
      }

      if (!selectedMimeType) {
        throw new Error('No supported audio format found')
      }

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: selectedMimeType,
      })

      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Stop audio level monitoring
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current)
        }
        setAudioLevel(0)

        // Stop timer
        if (timerRef.current) {
          clearInterval(timerRef.current)
        }

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())

        // Create blob from chunks
        const audioBlob = new Blob(audioChunksRef.current, {
          type: selectedMimeType,
        })

        // Send for transcription
        await sendForTranscription(audioBlob)
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start(1000) // Collect data every second

      // Start audio level monitoring
      updateAudioLevel()

      // Start duration timer
      startTimeRef.current = Date.now()
      setDuration(0)
      timerRef.current = setInterval(() => {
        setDuration(Math.floor((Date.now() - startTimeRef.current) / 1000))
      }, 1000)

      setState('recording')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start recording'
      setError(message)
      onError?.(message)
    }
  }, [onError, updateAudioLevel])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && state === 'recording') {
      setState('processing')
      mediaRecorderRef.current.stop()
    }
  }, [state])

  const sendForTranscription = async (audioBlob: Blob) => {
    try {
      const formData = new FormData()

      // Determine file extension from mime type
      let ext = '.webm'
      if (audioBlob.type.includes('ogg')) ext = '.ogg'
      if (audioBlob.type.includes('mp4')) ext = '.m4a'

      formData.append('audio', audioBlob, `recording${ext}`)
      formData.append('model', 'base')

      // Use interview endpoint if sessionId provided
      const endpoint = sessionId
        ? `${API_BASE}/voice/transcribe-for-interview`
        : `${API_BASE}/voice/transcribe`

      if (sessionId) {
        formData.append('session_id', sessionId)
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Transcription failed: ${response.status}`)
      }

      const data = await response.json()
      onTranscription(data.text, data.duration)
      setState('idle')
      setDuration(0)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Transcription failed'
      setError(message)
      onError?.(message)
      setState('idle')
      setDuration(0)
    }
  }

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Error Display */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 px-3 py-2 rounded-lg">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Recording Controls */}
      <div className="flex items-center gap-4">
        {/* Main Record Button */}
        <button
          onClick={state === 'recording' ? stopRecording : startRecording}
          disabled={disabled || state === 'processing'}
          className={`
            relative w-16 h-16 rounded-full flex items-center justify-center
            transition-all duration-200
            ${
              state === 'recording'
                ? 'bg-red-600 hover:bg-red-700'
                : state === 'processing'
                ? 'bg-csuite-card cursor-wait'
                : 'bg-csuite-accent hover:bg-csuite-accent/80'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          {state === 'recording' ? (
            <Square className="w-6 h-6 text-white" fill="white" />
          ) : state === 'processing' ? (
            <Loader2 className="w-6 h-6 text-white animate-spin" />
          ) : (
            <Mic className="w-6 h-6 text-white" />
          )}

          {/* Audio Level Ring */}
          {state === 'recording' && (
            <div
              className="absolute inset-0 rounded-full border-4 border-red-400 animate-pulse"
              style={{
                transform: `scale(${1 + audioLevel * 0.3})`,
                opacity: 0.5 + audioLevel * 0.5,
              }}
            />
          )}
        </button>

        {/* Audio Level Indicator */}
        {state === 'recording' && (
          <div className="flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-gray-400" />
            <div className="w-24 h-2 bg-csuite-card rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all duration-75"
                style={{ width: `${audioLevel * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Duration Display */}
      {(state === 'recording' || state === 'processing') && (
        <div className="text-gray-400 text-sm">
          {state === 'recording' && (
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              Recording: {formatDuration(duration)}
            </span>
          )}
          {state === 'processing' && (
            <span className="flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin" />
              Transcribing...
            </span>
          )}
        </div>
      )}

      {/* Instructions */}
      {state === 'idle' && !error && (
        <p className="text-gray-500 text-xs">
          Click to start recording. Speak clearly into your microphone.
        </p>
      )}
    </div>
  )
}
