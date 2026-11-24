// Owner email/password authentication for the static ULTRON frontend.
// The publishable key is public by design. Owner authorization is rechecked server-side.
const PROJECT_URL='https://euhmejpaswmdpsutbtse.supabase.co';
const PUBLISHABLE_KEY='sb_publishable_5QK9sdn3C4EIeB0Jy_8TDQ_UKAaZ-9l';
const SESSION_KEY='ultron-owner-auth-session-v1';
const CONTROL_URL=PROJECT_URL+'/functions/v1/training-control';
async function request(path,options={}){
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(PROJECT_URL+path,{method:options.method||'GET',headers:{apikey:PUBLISHABLE_KEY,'Content-Type':'application/json',...(options.token?{Authorization:'Bearer '+options.token}:{})},...(options.body?{body:JSON.stringify(options.body)}:{}),cache:'no-store',signal:controller.signal});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(payload.msg||payload.message||payload.error_description||payload.error||'Authentication request failed (HTTP '+response.status+').');
  return payload;
 }finally{clearTimeout(timer);}
}
function readSession(){try{return JSON.parse(localStorage.getItem(SESSION_KEY)||'null');}catch{return null;}}
function saveSession(session){try{localStorage.setItem(SESSION_KEY,JSON.stringify(session));}catch{throw new Error('This browser cannot save the sign-in session. Check browser storage settings.');}}
export function clearOwnerSession(){try{localStorage.removeItem(SESSION_KEY);}catch{}}
export async function signInOwner(email,password){
 const normalized=String(email||'').trim().toLowerCase();
 if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized))throw new Error('Enter a valid email address.');
 if(typeof password!=='string'||!password)throw new Error('Enter your password.');
 const data=await request('/auth/v1/token?grant_type=password',{method:'POST',body:{email:normalized,password}});
 if(!data.access_token||!data.refresh_token||!data.user?.id)throw new Error('Supabase returned an incomplete sign-in session.');
 saveSession({access_token:data.access_token,refresh_token:data.refresh_token,expires_at:data.expires_at||Math.floor(Date.now()/1000)+(data.expires_in||3600),user:{id:data.user.id,email:data.user.email||normalized}});
 return verifyOwner();
}
export async function getOwnerSession(){
 let session=readSession();if(!session?.access_token||!session?.refresh_token)return null;
 if(Number(session.expires_at||0)<=Math.floor(Date.now()/1000)+60){
  try{const data=await request('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:{refresh_token:session.refresh_token}});
   session={access_token:data.access_token,refresh_token:data.refresh_token,expires_at:data.expires_at||Math.floor(Date.now()/1000)+(data.expires_in||3600),user:{id:data.user?.id||session.user?.id,email:data.user?.email||session.user?.email}};saveSession(session);
  }catch{clearOwnerSession();throw new Error('Your sign-in session expired. Please sign in again.');}
 }
 return session;
}
export async function verifyOwner(){
 const session=await getOwnerSession();if(!session)return {signedIn:false,isOwner:false};
 const user=await request('/auth/v1/user',{token:session.access_token});
 if(user.id!==session.user.id){clearOwnerSession();throw new Error('The signed-in identity could not be verified.');}
 const response=await fetch(CONTROL_URL,{method:'POST',headers:{apikey:PUBLISHABLE_KEY,Authorization:'Bearer '+session.access_token,'Content-Type':'application/json'},body:JSON.stringify({action:'health'}),cache:'no-store'});
 const result=await response.json().catch(()=>({}));
 if(response.status===403)return {signedIn:true,isOwner:false,email:user.email||session.user.email,message:'This account is not the configured ULTRON owner.'};
 if(!response.ok||result.ok!==true)throw new Error(result.error||'Owner verification service is unavailable.');
 return {signedIn:true,isOwner:true,email:user.email||session.user.email,checks:result.checks||{}};
}
export async function signOutOwner(){
 const session=readSession();try{if(session?.access_token)await request('/auth/v1/logout',{method:'POST',token:session.access_token});}finally{clearOwnerSession();}
}
