import React from 'react'
import { motion } from 'framer-motion'

export default function ChatMessage({ message, index }) {
  const isBot = message.role === 'bot'
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className={`mb-8 flex gap-3 ${isBot ? 'flex-row' : 'flex-row-reverse'}`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isBot ? (
          // Professional travel agent bot avatar
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 flex items-center justify-center shadow-md">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        ) : (
          // Default user avatar
          <div className="w-10 h-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center shadow-md">
            <svg className="w-6 h-6 text-gray-600 dark:text-gray-300" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          </div>
        )}
      </div>

      {/* Message content container */}
      <div className={`flex flex-col ${isBot ? 'items-start' : 'items-end'} flex-1 min-w-0`}>
        {/* Meta info (who sent it) */}
        <div className={`text-xs uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2 ${isBot ? 'text-left' : 'text-right'}`}>
          {isBot ? 'Assistant' : 'You'}
        </div>
        
        {/* Message bubble */}
        <div className={`inline-block max-w-[85%] rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-3 break-words ${isBot ? 'bg-white dark:bg-[#2a2a2a] text-gray-800 dark:text-gray-200' : 'bg-blue-50 dark:bg-[#1e3a5f] text-gray-800 dark:text-gray-200'}`}>
          <p className="text-base leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>
      </div>
    </motion.div>
  )
}
