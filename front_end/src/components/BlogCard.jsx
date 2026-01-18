import React from 'react'
import { motion } from 'framer-motion'

export default function BlogCard({ post }) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="group bg-white rounded-xl overflow-hidden shadow-sm"
    >
      <a href="#" className="block">
        <div className="aspect-[3/2] overflow-hidden bg-gray-100">
          <img
            src={post.image}
            alt={post.title}
            className="w-full h-full object-cover transform transition-transform duration-700 group-hover:scale-105"
          />
        </div>
        <div className="p-6">
          <div className="meta-text mb-3">{post.meta}</div>
          <h3 className="text-2xl font-playfair font-light mb-3 group-hover:accent transition-colors">{post.title}</h3>
          <p className="text-sm text-gray-600">{post.excerpt}</p>
        </div>
      </a>
    </motion.article>
  )
}
