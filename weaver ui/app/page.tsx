'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RefreshCw, Play, Square } from 'lucide-react'

export default function Page() {
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState<string[]>([])

  const handleStart = () => {
    setIsRunning(true)
    setLogs(prev => ['Bot started', ...prev])
  }

  const handleStop = () => {
    setIsRunning(false)
    setLogs(prev => ['Bot stopped', ...prev])
  }

  return (
    <div className="min-h-screen p-4 font-mono bg-zinc-950 text-zinc-50">
      <div className="max-w-2xl mx-auto space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">WEAVER TRADING BOT</h1>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-sm font-mono text-zinc-400">Status:</span>
          <span className={`text-sm font-mono ${isRunning ? 'text-emerald-400' : 'text-zinc-500'}`}>
            {isRunning ? 'ACTIVE' : 'INACTIVE'}
          </span>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-mono text-zinc-400">Total Trades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-zinc-50">0</div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-mono text-zinc-400">Total Value</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-zinc-50">$1000.71</div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-mono text-zinc-400">Total P&L</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-zinc-500">$0.00</div>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-mono text-zinc-400">ROE</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-zinc-500">0.0%</div>
            </CardContent>
          </Card>
        </div>

        <div className="flex gap-2">
          <Button 
            variant="default"
            className="w-24 font-mono bg-emerald-600 hover:bg-emerald-700"
            onClick={handleStart}
            disabled={isRunning}
          >
            <Play className="w-4 h-4 mr-2" />
            Start
          </Button>
          <Button 
            variant="outline"
            className="w-24 font-mono bg-zinc-800 text-zinc-100 border-zinc-700 hover:bg-zinc-700 hover:text-zinc-50"
            onClick={handleStop}
            disabled={!isRunning}
          >
            <Square className="w-4 h-4 mr-2" />
            Stop
          </Button>
        </div>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="font-mono text-zinc-400">OPERATION LOG</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] overflow-auto space-y-2">
              {logs.map((log, index) => (
                <div key={index} className="text-sm text-zinc-500">
                  {log}
                </div>
              ))}
              {logs.length === 0 && (
                <div className="text-sm text-zinc-600">No operations logged yet</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

