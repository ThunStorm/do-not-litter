import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, Clipboard, FileText, Link2, ScanLine } from 'lucide-react'
import { FormEvent, useRef, useState } from 'react'

import { PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

export function CapturePage() {
  const [value, setValue] = useState('')
  const [message, setMessage] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const imageInput = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.jobs, refetchInterval: 4000 })
  const capture = useMutation({
    mutationFn: api.capture,
    onSuccess: () => {
      setValue('')
      setMessage('已交给 Mac mini 处理')
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error) => setMessage(error.message),
  })
  const upload = useMutation({
    mutationFn: api.captureFile,
    onSuccess: () => {
      setMessage('文件已安全接收，处理将在后台继续')
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error) => setMessage(error.message),
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    if (value.trim()) capture.mutate(value.trim())
  }

  function chooseFile(file?: File) {
    if (file) upload.mutate(file)
  }

  async function pasteClipboard() {
    try {
      const text = await navigator.clipboard.readText()
      setValue(text)
      setMessage(text ? '已从剪贴板读取，请确认后提交' : '剪贴板中没有文字')
    } catch {
      setMessage('浏览器未授予剪贴板读取权限，可直接粘贴到输入框')
    }
  }

  return (
    <div className="capture-page page-frame">
      <PageHeader title="投递" />
      <p className="page-lead">链接、文档或图片，都交给至简</p>
      <form className="capture-bar capture-bar--large" onSubmit={submit}>
        <Link2 /><input placeholder="粘贴链接或正文" value={value} onChange={(event) => setValue(event.target.value)} />
        <button className="capture-bar__submit" aria-label="提交" disabled={capture.isPending}><ArrowUp /></button>
      </form>
      {message && <p className="capture-message">{message}</p>}
      <input ref={fileInput} className="visually-hidden" type="file" accept=".docx,.pdf,.xlsx,.xlsm,.txt,.md,.png,.jpg,.jpeg" onChange={(event) => chooseFile(event.target.files?.[0])} />
      <input ref={imageInput} className="visually-hidden" type="file" accept="image/png,image/jpeg" capture="environment" onChange={(event) => chooseFile(event.target.files?.[0])} />
      <div className="capture-options">
        <button onClick={() => fileInput.current?.click()} disabled={upload.isPending}><FileText /><strong>上传文件</strong><span>DOCX / PDF / XLSX / 图片</span></button>
        <button onClick={() => imageInput.current?.click()} disabled={upload.isPending}><ScanLine /><strong>扫描文档</strong><span>调用相机后由 Vision OCR 识别</span></button>
        <button onClick={() => void pasteClipboard()}><Clipboard /><strong>从剪贴板</strong><span>读取后仍由你确认提交</span></button>
      </div>
      <section className="panel capture-jobs">
        <div className="panel__heading"><h2>正在处理</h2><span>可离开此页面，Mac mini 会继续处理</span></div>
        {jobs.data?.filter((job) => ['RUNNING', 'QUEUED'].includes(job.status)).slice(0, 3).map((job) => (
          <div className="capture-job" key={job.id}><div><strong>{job.title}</strong><span>{job.current_step} · {job.progress}%</span></div><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div></div>
        ))}
      </section>
    </div>
  )
}
