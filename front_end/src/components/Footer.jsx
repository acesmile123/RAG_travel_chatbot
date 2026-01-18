import React from 'react'

export default function Footer() {
  return (
    <footer className="border-t mt-12 py-8">
      <div className="max-w-6xl mx-auto px-6 text-sm text-gray-500 text-center">
        © {new Date().getFullYear()} — Built as a demo inspired by Leandra Isler
      </div>
    </footer>
  )
}
