import { useState, useEffect } from 'react'
import { X, CheckSquare, Square, AlertTriangle, Database, Globe, Rocket, RefreshCw } from 'lucide-react'
import { repoService } from '../services/repoService'

interface TestItem {
  test_name: string
  description: string
  priority: 'high' | 'medium' | 'low'
  status: 'pending' | 'passed' | 'failed'
}

interface TestingChecklistData {
  target_name: string
  target_type: string
  overall_criticality: string
  total_references: number
  unit_tests: TestItem[]
  integration_tests: TestItem[]
  api_tests: TestItem[]
  database_validation: TestItem[]
  deployment_verification: TestItem[]
  regression_tests: TestItem[]
}

interface Props {
  isOpen: boolean
  onClose: () => void
  repoId: string
  targetName: string
  targetType?: string
}

export default function TestingChecklistDrawer({ isOpen, onClose, repoId, targetName, targetType }: Props) {
  const [data, setData] = useState<TestingChecklistData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'unit' | 'integration' | 'api' | 'database' | 'deployment' | 'regression'>('unit')

  useEffect(() => {
    if (isOpen && repoId && targetName) {
      loadChecklist()
    }
  }, [isOpen, repoId, targetName])

  const loadChecklist = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await repoService.generateTestingChecklist(repoId, undefined, targetName, targetType)
      setData(result)
    } catch (err) {
      setError('Failed to generate testing checklist')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleTestStatus = (tab: 'unit' | 'integration' | 'api' | 'database' | 'deployment' | 'regression', index: number) => {
    if (!data) return
    setData(prev => {
      if (!prev) return prev
      let categoryTests: TestItem[]
      let categoryKey: keyof TestingChecklistData
      
      switch (tab) {
        case 'unit':
          categoryTests = prev.unit_tests
          categoryKey = 'unit_tests'
          break
        case 'integration':
          categoryTests = prev.integration_tests
          categoryKey = 'integration_tests'
          break
        case 'api':
          categoryTests = prev.api_tests
          categoryKey = 'api_tests'
          break
        case 'database':
          categoryTests = prev.database_validation
          categoryKey = 'database_validation'
          break
        case 'deployment':
          categoryTests = prev.deployment_verification
          categoryKey = 'deployment_verification'
          break
        case 'regression':
          categoryTests = prev.regression_tests
          categoryKey = 'regression_tests'
          break
      }
      
      return {
        ...prev,
        [categoryKey]: categoryTests.map((test, i) =>
          i === index
            ? { ...test, status: test.status === 'passed' ? 'pending' : 'passed' }
            : test
        )
      }
    })
  }

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high': return 'text-red-400 bg-red-500/10 border-red-500/20'
      case 'medium': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
      case 'low': return 'text-green-400 bg-green-500/10 border-green-500/20'
      default: return 'text-gray-400 bg-gray-500/10 border-gray-500/20'
    }
  }

  const getTabIcon = (tab: string) => {
    switch (tab) {
      case 'unit': return <CheckSquare className="w-4 h-4" />
      case 'integration': return <RefreshCw className="w-4 h-4" />
      case 'api': return <Globe className="w-4 h-4" />
      case 'database': return <Database className="w-4 h-4" />
      case 'deployment': return <Rocket className="w-4 h-4" />
      case 'regression': return <AlertTriangle className="w-4 h-4" />
      default: return <CheckSquare className="w-4 h-4" />
    }
  }

  const tabs = [
    { id: 'unit' as const, label: 'Unit Tests', count: data?.unit_tests.length || 0 },
    { id: 'integration' as const, label: 'Integration', count: data?.integration_tests.length || 0 },
    { id: 'api' as const, label: 'API Tests', count: data?.api_tests.length || 0 },
    { id: 'database' as const, label: 'Database', count: data?.database_validation.length || 0 },
    { id: 'deployment' as const, label: 'Deployment', count: data?.deployment_verification.length || 0 },
    { id: 'regression' as const, label: 'Regression', count: data?.regression_tests.length || 0 },
  ]

  const getTestsForTab = (tab: 'unit' | 'integration' | 'api' | 'database' | 'deployment' | 'regression'): TestItem[] => {
    if (!data) return []
    switch (tab) {
      case 'unit': return data.unit_tests
      case 'integration': return data.integration_tests
      case 'api': return data.api_tests
      case 'database': return data.database_validation
      case 'deployment': return data.deployment_verification
      case 'regression': return data.regression_tests
    }
  }

  const calculateProgress = (tests: TestItem[]) => {
    if (tests.length === 0) return 0
    const passed = tests.filter(t => t.status === 'passed').length
    return Math.round((passed / tests.length) * 100)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <div className="relative ml-auto h-full w-[700px] bg-[#09090b] border-l border-gray-800 shadow-2xl flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-xl font-semibold text-white">Testing Checklist</h2>
            {data && (
              <p className="text-sm text-gray-500 mt-1">
                {data.target_name} • {data.total_references} references
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Generating testing checklist...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full text-red-400">
              {error}
            </div>
          ) : data ? (
            <div className="p-6 space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-white">
                    {data.unit_tests.length + data.integration_tests.length + data.api_tests.length}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Total Tests</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-orange-400">
                    {data.unit_tests.filter(t => t.priority === 'high').length +
                     data.integration_tests.filter(t => t.priority === 'high').length +
                     data.api_tests.filter(t => t.priority === 'high').length}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">High Priority</div>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="text-2xl font-bold text-green-400">
                    {data.overall_criticality}
                  </div>
                  <div className="text-xs text-gray-500 uppercase tracking-wider">Criticality</div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex flex-wrap gap-2 border-b border-gray-800 pb-4">
                {tabs.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.id
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-800 text-gray-400 hover:text-white'
                    }`}
                  >
                    {getTabIcon(tab.id)}
                    {tab.label}
                    {tab.count > 0 && (
                      <span className="px-1.5 py-0.5 text-xs bg-white/20 rounded-full">
                        {tab.count}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Test List */}
              <div className="space-y-3">
                {getTestsForTab(activeTab).length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No tests in this category
                  </div>
                ) : (
                  getTestsForTab(activeTab).map((test, index) => (
                    <div
                      key={index}
                      className="bg-gray-900/30 rounded-lg border border-gray-800 p-4 hover:bg-gray-800/50 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <button
                          onClick={() => toggleTestStatus(activeTab, index)}
                          className="p-1 rounded hover:bg-gray-700 transition-colors mt-0.5"
                        >
                          {test.status === 'passed' ? (
                            <CheckSquare className="w-5 h-5 text-green-400" />
                          ) : (
                            <Square className="w-5 h-5 text-gray-500" />
                          )}
                        </button>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-white truncate">{test.test_name}</span>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full shrink-0 ${getPriorityColor(test.priority)}`}>
                              {test.priority}
                            </span>
                          </div>
                          <div className="text-sm text-gray-500">{test.description}</div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Progress */}
              {getTestsForTab(activeTab).length > 0 && (
                <div className="bg-gray-900/50 rounded-lg p-4 border border-gray-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">Progress</span>
                    <span className="text-sm font-medium text-white">
                      {calculateProgress(getTestsForTab(activeTab))}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full transition-all"
                      style={{ width: `${calculateProgress(getTestsForTab(activeTab))}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
