import React from 'react'

export default function Header() {
  return (
    <header className="py-10 bg-white">
      <div className="max-w-6xl mx-auto px-6 flex flex-col items-center">
        <h1 className="text-3xl font-playfair font-light">Leandra-inspired Blog</h1>
        <p className="text-sm text-gray-500 mt-2">Minimalist photography & essays</p>
        <nav className="text-sm text-gray-600 mt-4">
          <a className="mx-3 hover:text-gray-900" href="#">Home</a>
          <a className="mx-3 hover:text-gray-900" href="#">About</a>
          <a className="mx-3 hover:text-gray-900" href="#">Contact</a>
        </nav>
      </div>
    </header>
  )
}
