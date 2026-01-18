import { useState, useRef, useEffect } from 'react'
import { sendMessageToAI } from './services/api'
import { listSessions, getSession, createSession, deleteSession } from './services/sessions'
import ChatMessage from './components/ChatMessage'
import { motion } from 'framer-motion'

function App() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([
    { 
      role: 'bot', 
      content: 'Hello! I\'m here to help with your travel plans. Where would you like to go?', 
      sources: [] 
    }
  ])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const [sidebarOpen, setSidebarOpen] = useState(false) 
  const [historyOpen, setHistoryOpen] = useState(false)
  const [faqOpen, setFaqOpen] = useState(false)
  const [selectedFaq, setSelectedFaq] = useState(null)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  
  // Sessions state
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [isSyncing, setIsSyncing] = useState(false)
  
  // Dark mode state
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('theme')
      return saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    } catch {
      return 'light'
    }
  })

  // Apply theme to document
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    try {
      localStorage.setItem('theme', theme)
    } catch {}
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  const openSidebar = () => setSidebarOpen(true)
  const closeSidebar = () => setSidebarOpen(false)
  const toggleHistory = () => setHistoryOpen(v => !v)
  const toggleFaq = () => setFaqOpen(v => !v)
  
  // FAQ data with questions and answers
  const faqs = [
  { "id": 1, "question": "Đây là trang web gì?", "answer": "Hệ thống Trợ lý du lịch thông minh ứng dụng AI chuyên sâu cho 18 tỉnh thành Việt Nam." },
  { "id": 2, "question": "Tôi có thể hỏi những gì ở đây?", "answer": "Bạn có thể hỏi mọi thông tin về du lịch, ẩm thực và đi lại tại 18 tỉnh thành: Miền Bắc (Hà Nội, Hải Phòng, Quảng Ninh, Bắc Ninh, Cao Bằng, Lạng Sơn, Tuyên Quang) • Miền Trung (Đà Nẵng, Huế, Quảng Nam, Quảng Bình, Hà Tĩnh, Thanh Hóa) • Miền Nam (TP.HCM, Cần Thơ, Kiên Giang, Tây Ninh, Vũng Tàu). Chỉ cần nhập tên địa danh hoặc món ăn, AI sẽ hỗ trợ bạn ngay!"},
  { "id": 3, "question": "Chúng tôi là ai?", "answer": "Nhóm sinh viên CS thực hiện đồ án về RAG & Fine-tuning LLM cho ngành du lịch Việt Nam." },
  { "id": 4, "question": "Thông tin ở đây có chính xác không?", "answer": "Có! Hệ thống dùng RAG để truy xuất dữ liệu từ sách báo và web uy tín, hạn chế lỗi ảo tưởng của AI." },
  { "id": 5, "question": "Chatbot này có gì đặc biệt?", "answer": "Văn phong gần gũi, sành sỏi như người bản địa nhờ quá trình Fine-tuning đặc thù." },
  { "id": 6, "question": "Tôi có cần đăng nhập không?", "answer": "Không cần. Bạn có thể sử dụng ngay lập tức với quyền riêng tư được đảm bảo tuyệt đối." }
]
  
  const openFaqDetail = (faq) => {
    setSelectedFaq(faq)
  }
  
  const closeFaqDetail = () => {
    setSelectedFaq(null)
  }
  
  const openFeedback = () => {
    setFeedbackOpen(true)
  }
  
  const closeFeedback = () => {
    setFeedbackOpen(false)
  }

  // Session management functions
  const loadSessions = async () => {
    try {
      setIsSyncing(true)
      const data = await listSessions()
      setSessions(data)
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setIsSyncing(false)
    }
  }

  const selectSession = async (sessionId) => {
    try {
      const sessionData = await getSession(sessionId)
      setMessages(sessionData.messages || [])
      setCurrentSessionId(sessionId)
      closeSidebar()
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  const createNewSession = async () => {
    try {
      const now = new Date()
      const dateTime = now.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
      
      const newSession = await createSession({
        topic: dateTime,
        messages: []
      })
      
      // Reset chat và set session mới
      setMessages([{ 
        role: 'bot', 
        content: 'Hello! I\'m here to help with your travel plans. Where would you like to go?', 
        sources: [] 
      }])
      setCurrentSessionId(newSession.id)
      
      // Thêm vào danh sách sessions
      setSessions(prev => [newSession, ...prev])
      closeSidebar()
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  const removeSession = async (sessionId, event) => {
    event.stopPropagation()
    try {
      await deleteSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      
      // Nếu đang xem session bị xóa thì reset
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null)
        setMessages([{ 
          role: 'bot', 
          content: 'Hello! I\'m here to help with your travel plans. Where would you like to go?', 
          sources: [] 
        }])
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  // Load sessions khi mở lịch sử
  useEffect(() => {
    if (historyOpen && sessions.length === 0) {
      loadSessions()
    }
  }, [historyOpen])

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') closeSidebar()
    }
    if (sidebarOpen) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [sidebarOpen])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMsg = { role: 'user', content: input, sources: [] }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    // Reset textarea height to default
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    try {
      const data = await sendMessageToAI(input)
      const botMsg = { role: 'bot', content: data.text, sources: data.sources }
      setMessages(prev => [...prev, botMsg])
    } catch (error) {
      console.error('Error:', error)
      const errorMsg = { role: 'bot', content: 'Sorry, something went wrong. Please try again.', sources: [] }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="min-h-screen bg-[#fcfcfc] dark:bg-[#1a1a1a] flex flex-col">
      
      {/* Header - minimal and elegant */}
      <header className="sticky top-0 z-10 border-b border-gray-200 dark:border-gray-700 py-6 bg-white dark:bg-gray-900 relative">
        <button
          aria-label="Open sidebar"
          aria-expanded={sidebarOpen}
          onClick={openSidebar}
          className="absolute left-4 top-1/2 -translate-y-1/2 p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <svg className="w-6 h-6 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>

        <div className="max-w-4xl mx-auto px-6 text-center">
          <h1 className="text-2xl font-light tracking-tight text-gray-800 dark:text-gray-200">Travel Assistant</h1>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Your personal guide to exploring the world</p>
        </div>

        {/* Theme toggle button */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle dark mode"
          className="absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          {theme === 'dark' ? (
            <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-gray-700" fill="currentColor" viewBox="0 0 20 20">
              <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
            </svg>
          )}
        </button>
      </header>

      {/* Chat container */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 pt-12 pb-48">
            {messages.map((msg, index) => (
              <ChatMessage key={index} message={msg} index={index} />
            ))}
            
            {/* Loading indicator - minimal */}
            {isLoading && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-left mb-8"
              >
                <div className="text-xs uppercase tracking-wider text-gray-400 mb-2">Assistant</div>
                <div className="inline-flex items-center gap-2 text-sm text-gray-400">
                  <span>Thinking</span>
                  <span className="flex gap-1">
                    <span className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </span>
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      {/* Fixed composer: floats above messages and stays locked on scroll */}
      <div className="fixed left-1/2 bottom-10 z-50 w-full max-w-4xl px-6 -translate-x-1/2">
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 flex items-center px-4 py-2.5">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about travel..."
              disabled={isLoading}
              rows={1}
              className="w-full px-3 py-0 text-base text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 bg-transparent border-0 focus:outline-none resize-none custom-scrollbar"
              style={{ maxHeight: '150px', height: '28px', lineHeight: '28px' }}
              onInput={(e) => {
                const target = e.target
                target.style.height = '28px'
                const newHeight = Math.min(target.scrollHeight, 150)
                target.style.height = newHeight + 'px'
                target.style.lineHeight = newHeight > 28 ? '1.5' : '28px'
              }}
            />
          </div>

          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
            title="Send message"
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
              !input.trim() || isLoading ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-default' : 'bg-gray-800 dark:bg-gray-600 text-white hover:bg-gray-700 dark:hover:bg-gray-500 cursor-pointer'
            }`}
          >
            {/* Send icon (paper plane) */}
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
            <span className="sr-only">Send</span>
          </button>
        </div>

        <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 text-center">
          Lưu ý: Mô hình có thể đưa ra câu trả lời không chính xác ở một số trường hợp, vì vậy hãy luôn kiểm chứng thông tin bạn nhé!
        </p>
      </div>

      {/* Sidebar overlay */}
      <div className={`fixed inset-0 z-50 ${sidebarOpen ? 'block' : 'pointer-events-none'}`} aria-hidden={!sidebarOpen}>
        <div
          className={`absolute inset-0 bg-black/40 transition-opacity ${sidebarOpen ? 'opacity-100' : 'opacity-0'}`}
          onClick={closeSidebar}
        />

        <aside
          className={`absolute left-0 top-0 bottom-0 w-72 bg-white dark:bg-gray-900 shadow-xl transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300`}
          role="dialog"
          aria-modal="true"
        >
          <div className="p-4 flex items-center justify-between border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-sm font-medium text-gray-800 dark:text-gray-200">Menu</h2>
            <button aria-label="Close sidebar" onClick={closeSidebar} className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
              <svg className="w-6 h-6 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <nav className="p-4 space-y-2">
            <button 
              onClick={createNewSession}
              className="w-full text-left text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded flex items-center gap-2"
            >
              Cuộc hội thoại mới
            </button>

            <div>
              <button onClick={toggleHistory} aria-expanded={historyOpen} className="w-full text-left flex items-center justify-between text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded">
                <span className="flex items-center gap-2">
                  Lịch sử hội thoại
                </span>
                <svg className={`w-4 h-4 text-gray-500 dark:text-gray-400 transform transition-transform duration-200 ${historyOpen ? 'rotate-180' : ''}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/></svg>
              </button>

              {/* Sessions list */}
              <div className={`${historyOpen ? 'block' : 'hidden'} mt-2 ml-3 space-y-1 text-sm text-gray-600 dark:text-gray-400`}>
                {isSyncing ? (
                  <div className="p-2 text-center text-gray-400">Đang tải...</div>
                ) : sessions.length === 0 ? (
                  <div className="p-2 text-center text-gray-400">Chưa có lịch sử</div>
                ) : (
                  sessions.map(session => (
                    <div
                      key={session.id}
                      className="group relative flex items-center justify-between p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                      onClick={() => selectSession(session.id)}
                    >
                      <span className="flex-1 truncate">{session.topic}</span>
                      <button
                        onClick={(e) => removeSession(session.id, e)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                        title="Xóa"
                      >
                        🗑️
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div>
              <button onClick={toggleFaq} aria-expanded={faqOpen} className="w-full text-left flex items-center justify-between text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded">
                FAQs
                <svg className={`w-4 h-4 text-gray-500 dark:text-gray-400 transform transition-transform duration-200 ${faqOpen ? 'rotate-180' : ''}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/></svg>
              </button>

              {/* FAQ list (toggleable) */}
              <div className={`${faqOpen ? 'block' : 'hidden'} mt-2 ml-3 space-y-1 text-sm text-gray-600 dark:text-gray-400`}>
                {faqs.map(faq => (
                  <button 
                    key={faq.id}
                    onClick={() => openFaqDetail(faq)}
                    className="block w-full text-left p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    {faq.question}
                  </button>
                ))}
              </div>
            </div>

            <button onClick={openFeedback} className="w-full text-left text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 p-2 rounded">Báo lỗi / Góp ý</button>
          </nav>
        </aside>
      </div>

      {/* FAQ Detail Panel - Right Side */}
      <div className={`fixed inset-0 z-50 ${selectedFaq ? 'block' : 'pointer-events-none'}`} aria-hidden={!selectedFaq}>
        <div
          className={`absolute inset-0 bg-black/40 transition-opacity ${selectedFaq ? 'opacity-100' : 'opacity-0'}`}
          onClick={closeFaqDetail}
        />

        <aside
          className={`absolute right-0 top-0 bottom-0 w-96 bg-white dark:bg-gray-900 shadow-xl transform ${selectedFaq ? 'translate-x-0' : 'translate-x-full'} transition-transform duration-300`}
          role="dialog"
          aria-modal="true"
        >
          <div className="p-4 flex items-center justify-between border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-sm font-medium text-gray-800 dark:text-gray-200">FAQ Detail</h2>
            <button aria-label="Close FAQ detail" onClick={closeFaqDetail} className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
              <svg className="w-6 h-6 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          {selectedFaq && (
            <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 80px)' }}>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">{selectedFaq.question}</h3>
              <p className="text-base text-gray-600 dark:text-gray-400 leading-relaxed">{selectedFaq.answer}</p>
            </div>
          )}
        </aside>
      </div>

      {/* Feedback Panel - Right Side */}
      <div className={`fixed inset-0 z-50 ${feedbackOpen ? 'block' : 'pointer-events-none'}`} aria-hidden={!feedbackOpen}>
        <div
          className={`absolute inset-0 bg-black/40 transition-opacity ${feedbackOpen ? 'opacity-100' : 'opacity-0'}`}
          onClick={closeFeedback}
        />

        <aside
          className={`absolute right-0 top-0 bottom-0 w-96 bg-white dark:bg-gray-900 shadow-xl transform ${feedbackOpen ? 'translate-x-0' : 'translate-x-full'} transition-transform duration-300`}
          role="dialog"
          aria-modal="true"
        >
          <div className="p-4 flex items-center justify-between border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-sm font-medium text-gray-800 dark:text-gray-200">Báo lỗi / Góp ý</h2>
            <button aria-label="Close feedback" onClick={closeFeedback} className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
              <svg className="w-6 h-6 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 80px)' }}>
            <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); alert('Cảm ơn bạn đã gửi góp ý!'); closeFeedback(); }}>
              <div>
                <label htmlFor="feedback-content" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Nội dung
                </label>
                <textarea
                  id="feedback-content"
                  rows={6}
                  className="w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  placeholder="Vui lòng mô tả chi tiết vấn đề hoặc góp ý của bạn..."
                  required
                />
              </div>
              
              <div>
                <label htmlFor="feedback-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Email liên hệ
                </label>
                <input
                  type="email"
                  id="feedback-email"
                  className="w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="your.email@example.com"
                  required
                />
              </div>

              <button
                type="submit"
                className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800 rounded-md transition-colors"
              >
                Gửi góp ý
              </button>
              
              <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
                Chúng tôi sẽ phản hồi qua email trong vòng 24-48 giờ.
              </p>
            </form>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default App