import React, {FormEvent, useEffect, useRef, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

type DocumentInfo = {doc_id: string; filename: string; pages: number};
type Source = {doc_id: string; filename: string; pdf_page: number; evidence_id?: string};
type Answer = {answer: string; citations: Source[]; warnings: string[]; provider_mode: string; status: "answered" | "abstained"};
type Turn = {question: string; answer?: Answer; error?: string};

function fileName(path: string) {
  return path.split("/").pop() || path;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {...init, signal: AbortSignal.timeout(22000)});
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new Error(typeof problem.detail === "string" ? problem.detail : "No se pudo completar la solicitud.");
  }
  return response.json();
}

function PageViewer({source, close}: {source: Source; close: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const el = dialog.current!;
    el.showModal();
    return () => el.close();
  }, []);
  const url = "/api/documents/" + encodeURIComponent(source.doc_id) + "/pages/" + source.pdf_page + "/image";
  return <dialog ref={dialog} aria-labelledby="source-title" onCancel={close}
    onClick={e => { if (e.target === dialog.current) close(); }}>
    <article className="viewer">
      <header><div><small>DOCUMENTO ORIGINAL</small><h2 id="source-title">{fileName(source.filename)}</h2></div>
        <button autoFocus className="close" onClick={close} aria-label="Cerrar visor">×</button></header>
      <div className="page-label">Página PDF {source.pdf_page}</div>
      {failed ? <div role="alert" className="image-error">No se pudo abrir la página original.
        <button onClick={() => {setRetry(retry + 1); setFailed(false);}}>Reintentar</button></div>
        : <img key={retry} src={url + "?intento=" + retry} alt={"Página original " + source.pdf_page} onError={() => setFailed(true)}/>}
    </article>
  </dialog>;
}

function App() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [catalogError, setCatalogError] = useState(false);
  const [filter, setFilter] = useState("");
  const [library, setLibrary] = useState(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const latest = useRef<HTMLElement>(null);
  async function load() {
    setLoading(true); setCatalogError(false);
    try { setDocs(await json<DocumentInfo[]>("/api/documents")); }
    catch { setCatalogError(true); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => { latest.current?.scrollIntoView({block: "nearest"}); }, [turns.length, pending]);
  function open(target: Source) {
    trigger.current = document.activeElement as HTMLElement;
    setSource(target);
  }
  function close() {
    setSource(null);
    requestAnimationFrame(() => trigger.current?.focus());
  }
  async function ask(text: string, replace = false) {
    const q = text.trim();
    if (!q || pending) return;
    setPending(true); setQuestion("");
    setTurns(previous => [...(replace ? previous.slice(0, -1) : previous), {question: q}]);
    try {
      const answer = await json<Answer>("/api/chat", {method: "POST",
        headers: {"Content-Type": "application/json"}, body: JSON.stringify({message: q})});
      setTurns(previous => [...previous.slice(0, -1), {question: q, answer}]);
    } catch (e) {
      const error = e instanceof Error ? e.message : "Error al consultar los documentos.";
      setTurns(previous => [...previous.slice(0, -1), {question: q, error}]);
    } finally { setPending(false); }
  }
  function submit(e: FormEvent) { e.preventDefault(); void ask(question); }
  const suggestions = ["¿Qué es el riesgo de crédito?", "¿Qué políticas de liquidez se mencionan?"];
  return <>
    <header className="mast"><div className="mast-inner"><span className="brandmark" aria-hidden="true">F</span>
      <span className="brand">Archivo financiero</span><span className="header-rule"></span>
      <span className="muted mast-sub">Investigación documental</span>
      <button className="mobile-library" aria-expanded={library} aria-controls="library" onClick={() => setLibrary(!library)}>Biblioteca</button>
    </div></header>
    <div className="workspace">
      <aside id="library" className={library ? "library visible" : "library"}>
        <div className="library-heading"><h2>Biblioteca</h2><span aria-label="Documentos indexados" className="count">{docs.length}</span></div>
        <label className="filter-label">Filtrar documentos<input type="search" value={filter}
          onChange={e => setFilter(e.target.value)} placeholder="Nombre del reporte"/></label>
        {loading ? <p role="status">Cargando biblioteca…</p> : catalogError ? <p role="alert">Biblioteca no disponible. <button onClick={load}>Reintentar</button></p> : null}
        {!loading && !catalogError && docs.length === 0 && <p>Aún no hay documentos indexados.</p>}
        <ul>{docs.filter(d => d.filename.toLocaleLowerCase().includes(filter.toLocaleLowerCase())).map(d =>
          <li key={d.doc_id}><button className="document" onClick={() => open({...d, pdf_page: 1})}>
            <span className="paper" aria-hidden="true">PDF</span><span><strong>{fileName(d.filename)}</strong>
            <small>{d.pages} páginas</small></span></button></li>)}</ul>
        {docs.length > 0 && !docs.some(d => d.filename.toLowerCase().includes(filter.toLowerCase())) && <p>Sin coincidencias.</p>}
      </aside>
      <main>
        <div className="intro"><div className="section-label">CONSULTA DOCUMENTAL</div><h1>Asistente financiero</h1>
          <p>Consulta los reportes indexados y verifica cada respuesta en su página original.</p></div>
        {!turns.length && <div className="suggestions"><h2>Preguntas sugeridas</h2>{suggestions.map(s =>
          <button key={s} onClick={() => {setQuestion(s); input.current?.focus();}}>{s}<span aria-hidden="true">↗</span></button>)}</div>}
        <div className="thread" aria-live="polite">{turns.map((t, i) => <section key={i} ref={i===turns.length-1 ? latest : undefined}>
          <h2>{t.question}</h2>{t.answer ? <div className="result"><small>{t.answer.status === "answered" ? "EVIDENCIA RECUPERADA" : "EVIDENCIA INSUFICIENTE"}</small>
            <p>{t.answer.answer}</p>{t.answer.citations.map(c => <button className="citation" key={c.evidence_id} onClick={() => open(c)}>
              <strong>{fileName(c.filename)}</strong><span>Página {c.pdf_page} ↗</span></button>)}
            <footer>Modo {t.answer.provider_mode}</footer></div> :
            t.error ? <div role="alert" className="result error">{t.error} {i===turns.length-1 && <button onClick={() => void ask(t.question,true)}>Reintentar</button>}</div>
              : <p role="status">Buscando evidencia en los documentos…</p>}</section>)}</div>
        <form onSubmit={submit}><label htmlFor="message">Tu pregunta</label>
          <textarea id="message" ref={input} maxLength={1200} rows={2} value={question}
            placeholder="Pregunta por una cifra, un concepto o una nota del reporte…"
            onChange={e => setQuestion(e.target.value)} onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); void ask(question);}
            }}/>
          <div className="form-foot"><span>Solo documentos de la biblioteca</span><button type="submit" disabled={pending || !question.trim()}>Consultar <span aria-hidden="true">→</span></button></div>
        </form>
      </main>
    </div>
    {source && <PageViewer source={source} close={close}/>}
  </>;
}

createRoot(document.getElementById("root")!).render(<App/>);
