import type { Dataset } from './types';
const API = location.hostname === 'www.guopq.com' ? 'https://api.guopq.com/capitol-lens/api' : '/capitol-lens/api';
let pending: Promise<Dataset> | undefined;
async function db(){return new Promise<IDBDatabase>((resolve,reject)=>{const r=indexedDB.open('capitol-private-cache',1);r.onupgradeneeded=()=>r.result.createObjectStore('snapshots');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
async function read(key:string){const d=await db();try{return await new Promise<Dataset|undefined>((resolve,reject)=>{const r=d.transaction('snapshots').objectStore('snapshots').get(key);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}finally{d.close();}}
async function write(key:string,value:Dataset){const d=await db();try{await new Promise<void>((resolve,reject)=>{const tx=d.transaction('snapshots','readwrite');tx.objectStore('snapshots').clear();tx.objectStore('snapshots').put(value,key);tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);});}finally{d.close();}}
export function loadDataset(){
 if(pending)return pending;
 pending=(async()=>{
  // Authenticated lightweight manifest is checked before accessing any persistent data.
  const response=await fetch(`${API}/dataset-version`,{credentials:'include',cache:'no-store'});
  if(!response.ok)throw Error('Access could not be verified. Please sign in and retry.');
  const {version}=await response.json() as {version:string};
  let cached:Dataset|undefined;try{cached=await read(version);}catch{/* private browsing: network fallback */}
  if(cached)return cached;
  const r=await fetch(`${API}/dataset`,{credentials:'include'});if(!r.ok)throw Error('The research dataset is unavailable.');
  const value=await r.json() as Dataset;
  try{await write(version,value);}catch{/* quota errors never block research */}
  return value;
 })().finally(()=>{pending=undefined;});return pending;
}
