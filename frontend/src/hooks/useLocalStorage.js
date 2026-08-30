import { useState, useEffect, useCallback, useRef } from 'react'

export default function useLocalStorage(key, defaultValue) {
  // 首次读取是否失败（读取或解析异常）：失败时不能把默认值写回 localStorage，避免覆盖已保存的数据
  const readFailed = useRef(false)
  // 初始值引用：读取失败时，只有值真正被用户修改后才允许写回
  const initialValueRef = useRef(null)
  const defaultValueRef = useRef(defaultValue)
  defaultValueRef.current = defaultValue

  const [value, setValue] = useState(() => {
    try {
      const stored = localStorage.getItem(key)
      if (stored === null) return defaultValue // 从未保存过，使用默认值
      const parsed = JSON.parse(stored)
      initialValueRef.current = parsed
      return parsed
    } catch (e) {
      // 读取/解析失败：保留 localStorage 中已有数据，本次会话先用默认值
      readFailed.current = true
      initialValueRef.current = defaultValue
      console.warn(`读取 localStorage "${key}" 失败，保留已保存的数据：`, e)
      return defaultValue
    }
  })

  // 值变化时写回 localStorage
  useEffect(() => {
    // 读取失败且值未被修改：不写回，防止用默认值清空已保存的配置
    if (readFailed.current && value === initialValueRef.current) return
    try {
      // 已存储内容与待写入值一致时不重复写入，
      // 避免用本页的陈旧状态覆盖其他标签页刚写入的新值
      if (localStorage.getItem(key) === JSON.stringify(value)) return
      localStorage.setItem(key, JSON.stringify(value))
    } catch (e) {
      console.warn('Failed to save to localStorage:', e)
    }
  }, [key, value])

  // 跨标签页同步：其他标签页修改该 key 时，本页跟随最新值
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key !== key) return
      if (e.newValue === null) {
        setValue(defaultValueRef.current)
        return
      }
      try {
        setValue(JSON.parse(e.newValue))
      } catch {
        // 解析失败时保持当前状态，不覆盖本地存储
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [key])

  const remove = useCallback(() => {
    try {
      localStorage.removeItem(key)
      setValue(defaultValueRef.current)
    } catch (e) {
      console.warn('Failed to remove from localStorage:', e)
    }
  }, [key])

  return [value, setValue, remove]
}
