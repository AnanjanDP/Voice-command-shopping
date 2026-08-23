import { useCallback, useEffect, useRef, useState } from 'react'

export function useSpeechRecognition({ language, onResult, onError }) {
  const recognitionRef = useRef(null)
  const [supported, setSupported] = useState(true)
  const [isListening, setIsListening] = useState(false)
  const [interim, setInterim] = useState('')

  useEffect(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) { setSupported(false); return undefined }
    const recognition = new Recognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    recognition.onstart = () => { setIsListening(true); setInterim('') }
    recognition.onend = () => setIsListening(false)
    recognition.onerror = (event) => { setIsListening(false); onError?.(event.error) }
    recognition.onresult = (event) => {
      let phrase = ''
      let finalPhrase = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        phrase += event.results[i][0].transcript
        if (event.results[i].isFinal) finalPhrase += event.results[i][0].transcript
      }
      setInterim(phrase)
      if (finalPhrase) onResult(finalPhrase.trim())
    }
    recognitionRef.current = recognition
    return () => recognition.abort()
  }, [onError, onResult])

  const toggle = useCallback(() => {
    const recognition = recognitionRef.current
    if (!recognition) return
    recognition.lang = language
    if (isListening) recognition.stop()
    else recognition.start()
  }, [isListening, language])

  return { supported, isListening, interim, toggle }
}
