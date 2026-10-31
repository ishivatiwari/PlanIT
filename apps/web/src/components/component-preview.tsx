"use client";

import { useRef, useState, type FormEvent } from "react";
import { Button } from "./ui/button";
import { Badge, Card } from "./ui/card";
import { Dialog } from "./ui/dialog";
import { TextField, SelectField } from "./ui/field";
import { LoadingState, Message } from "./ui/feedback";
import { Icon } from "./icon";

export function ComponentPreview() {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [tone, setTone] = useState("Classic");
  const [error, setError] = useState("");
  const [sample, setSample] = useState({
    label: "A gathering to remember",
    tone: "Classic",
  });
  const [feedback, setFeedback] = useState("");
  const input = useRef<HTMLInputElement>(null);

  function updateSample(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!label.trim()) {
      setError("Enter a label for the sample card.");
      setFeedback("");
      input.current?.focus();
      return;
    }
    setError("");
    setSample({ label: label.trim(), tone });
    setFeedback("Sample updated in this page only. Nothing has been saved.");
  }

  function resetSample() {
    setLabel("");
    setTone("Classic");
    setError("");
    setSample({ label: "A gathering to remember", tone: "Classic" });
    setFeedback("Sample reset to its original appearance.");
  }

  return (
    <div className="gallery">
      <Message title="An interactive component preview">
        These examples only change this page. They do not create an event or
        save your information.
      </Message>
      <section className="section-block" aria-labelledby="palette-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">01 / Color & type</span>
            <h2 id="palette-title">A considered palette.</h2>
          </div>
        </div>
        <div className="palette-grid">
          <Card className="palette-card">
            <div className="color-swatch swatch-forest" />
            <strong>Forest</strong>
            <span>Grounded, clear, confident</span>
          </Card>
          <Card className="palette-card">
            <div className="color-swatch swatch-sage" />
            <strong>Sage</strong>
            <span>A little room to breathe</span>
          </Card>
          <Card className="palette-card">
            <div className="color-swatch swatch-ivory" />
            <strong>Ivory</strong>
            <span>A warm welcome</span>
          </Card>
          <Card className="type-card">
            <span className="type-specimen">Aa</span>
            <strong>Warmth meets clarity</strong>
            <span>
              Expressive serif headings.
              <br />
              Simple, readable body text.
            </span>
          </Card>
        </div>
      </section>
      <section className="section-block" aria-labelledby="controls-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">02 / Buttons & dialogs</span>
            <h2 id="controls-title">A clear next step.</h2>
          </div>
        </div>
        <Card className="control-card">
          <div className="button-row">
            <Button onClick={() => setOpen(true)}>
              Open example dialog <Icon name="arrow" />
            </Button>
            <Button variant="secondary" onClick={resetSample}>
              Reset sample
            </Button>
            <Button variant="ghost" onClick={() => setOpen(true)}>
              About this example
            </Button>
            <Button disabled>Coming soon</Button>
          </div>
          <p className="caption">
            Buttons describe their action. Unavailable actions stay visibly
            disabled.
          </p>
        </Card>
      </section>
      <section className="section-block" aria-labelledby="forms-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">03 / Forms & cards</span>
            <h2 id="forms-title">Small details. Clear guidance.</h2>
          </div>
        </div>
        <div className="gallery-form-grid">
          <Card>
            <form noValidate onSubmit={updateSample} className="sample-form">
              <TextField
                ref={input}
                label="Preview label"
                hint="Use a sample phrase, up to 80 characters. It is not saved."
                required
                maxLength={80}
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                error={error}
              />
              <SelectField
                label="Tone"
                value={tone}
                onChange={(event) => setTone(event.target.value)}
              >
                <option>Classic</option>
                <option>Playful</option>
                <option>Natural</option>
              </SelectField>
              {error && (
                <Message tone="error" title="Check the preview label" announce>
                  {error}
                </Message>
              )}
              <Button type="submit">Update sample card</Button>
            </form>
          </Card>
          <Card className="sample-card" aria-labelledby="sample-title">
            <Badge>Local example</Badge>
            <span className="sample-art" aria-hidden="true">
              <Icon name="spark" />
            </span>
            <h3 id="sample-title">{sample.label}</h3>
            <p>{sample.tone} style</p>
            <span className="caption">
              A component example, ready for your ideas.
            </span>
          </Card>
        </div>
        <p className="sample-feedback" role="status">
          {feedback}
        </p>
      </section>
      <section className="section-block" aria-labelledby="feedback-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">04 / Feedback</span>
            <h2 id="feedback-title">Always know where you stand.</h2>
          </div>
          <Badge>Example states</Badge>
        </div>
        <div className="feedback-grid">
          <Card>
            <h3 className="example-title">Example loading state</h3>
            <LoadingState label="Example: loading a workspace" />
            <p className="caption">A visual sample; no request is running.</p>
          </Card>
          <div className="message-stack">
            <Message tone="error" title="Example error message">
              Something could not be loaded. A real error would include a
              relevant retry action.
            </Message>
            <Message tone="success" title="Example success message">
              Completed actions receive clear, specific feedback.
            </Message>
          </div>
        </div>
      </section>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="A moment of clarity"
        description="This is a reusable dialog example."
      >
        <p>
          Dialogs keep a focused task in view. Use Tab to move between controls,
          or press Escape to return to the page.
        </p>
        <p>This example makes no changes.</p>
        <div className="dialog-actions">
          <Button onClick={() => setOpen(false)}>Back to the preview</Button>
        </div>
      </Dialog>
    </div>
  );
}
