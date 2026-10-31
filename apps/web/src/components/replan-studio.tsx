"use client";

import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { RequireAccount } from "./auth-provider";
import { Button, ButtonLink } from "./ui/button";
import { Card } from "./ui/card";
import { LoadingState, Message } from "./ui/feedback";

type Event={title:string;revision:number}; type Proposal={id:string;change_type:string;impact:Record<string,unknown>;alternative:Record<string,unknown>;status:string;accepted_plan_id:string|null};
export function ReplanStudio({eventId}:{eventId:string}) {
  const [event,setEvent]=useState<Event|null>(null); const [kind,setKind]=useState("guest_count"); const [value,setValue]=useState(""); const [proposal,setProposal]=useState<Proposal|null>(null); const [message,setMessage]=useState(""); const [loading,setLoading]=useState(true);
  async function refresh(){try{setEvent(await api<Event>(`/events/${eventId}`));}catch(e){setMessage(errorMessage(e));}finally{setLoading(false);}}
  // The refresh closure is scoped to the selected event.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(()=>{const t=window.setTimeout(()=>void refresh(),0);return()=>window.clearTimeout(t)},[eventId]);
  async function propose(){if(!event)return; const details=kind==="guest_count"?{guest_count:Number(value)}:kind==="budget_constraint"?{budget_ceiling_minor:Number(value)}:kind==="quote_increase"?{category:"Catering",increase_minor:Number(value)}:{note:value}; try{setProposal(await api<Proposal>(`/events/${eventId}/replans`,{method:"POST",revision:event.revision,data:{change_type:kind,details}}));setMessage("")}catch(e){setMessage(errorMessage(e))}}
  async function close(action:"approve"|"reject"){if(!proposal||!event)return;try{setProposal(await api<Proposal>(`/events/${eventId}/replans/${proposal.id}/${action}`,{method:"POST",revision:event.revision,data:{}}));await refresh();}catch(e){setMessage(errorMessage(e))}}
  return <RequireAccount>{loading?<LoadingState label="Opening adaptive replanning..."/>:<main className="workspace-main"><ButtonLink href={`/events/${eventId}`} variant="ghost">Back to event</ButtonLink><p className="eyebrow">Adaptive replanning</p><h1>{event?.title}</h1><p className="section-description">Every proposal starts from the current authorized plan. Review the impact and trade-offs before accepting it.</p>{message&&<Message tone="error" title="Replanning needs attention">{message}</Message>}<Card><h2>Describe a change</h2><label>Scenario<select value={kind} onChange={e=>setKind(e.target.value)}><option value="guest_count">Guest count change</option><option value="venue_change">Venue cancellation or replacement</option><option value="quote_increase">Vendor quote increase</option><option value="date_change">Event date change</option><option value="task_delay">Task delay</option><option value="budget_constraint">New budget constraint</option></select></label><label>Change detail<input value={value} onChange={e=>setValue(e.target.value)} placeholder={kind==="guest_count"?"New guest count":"Amount or note"}/></label><Button onClick={()=>void propose()}>Analyse impact</Button></Card>{proposal&&<Card><h2>Before and after review</h2><p>Status: {proposal.status}</p><pre>{JSON.stringify(proposal.impact,null,2)}</pre><h3>Proposed alternative</h3><p>Review the updated plan data before accepting. Completed work and the prior version remain preserved.</p>{proposal.status==="pending"&&<div><Button onClick={()=>void close("approve")}>Accept proposed changes</Button> <Button onClick={()=>void close("reject")} variant="ghost">Reject proposal</Button></div>}</Card>}</main>}</RequireAccount>;
}
