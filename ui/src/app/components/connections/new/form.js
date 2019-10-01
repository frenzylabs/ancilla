//
//  form.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 09/27/19
//  Copyright 2019 Wess Cope
//

import React from 'react'

import {
  Form,
  Button,
  Segment,
  Message,
  Icon
} from 'semantic-ui-react'

import {default as Printer} from '../../../network/printer'

export default class ConnectionForm extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      name: null,
      port: null,
      ports: [],
      baudrates: [],
      baudrate: 115200,
      hasError: false,
      isSaving: false
    }

    this.renderSpinner    = this.renderSpinner.bind(this)
    this.portOptions      = this.portOptions.bind(this)
    this.baudrateOptions  = this.baudrateOptions.bind(this)
    this.cancelAction     = this.cancelAction.bind(this)
    this.submitAction     = this.submitAction.bind(this)
  }

  cancelAction(e) {
    if(e) { 
      e.preventDefault() 
    }

    if(this.props.closeAction) {
      this.props.closeAction()
    }
  }

  portOptions() {
    return (this.state.ports || []).map((port, idx) => { 
      return {
        key:    `${port}-${idx + 1}`, 
        value:  port, 
        text:   port
      } 
    })
  }

  baudrateOptions() {
    return (this.state.baudrates || []).map((rate, idx) => {
      return {
        key:    `RATE-${rate}-${idx + 1}`,
        value:  rate,
        text:   `${rate}`
      }
    })
  }

  submitAction(e) {
    e.preventDefault()

    Printer.create({name: this.state.name, port: this.state.port, baud_rate: this.state.baudrate})
    .then((res) => {
      console.log("RES: ", res)
    })
    .catch((err) => {
      console.log("ERR: ", err)
    })
  }

  renderSpinner() {
    return(
      <Message icon>
      <Icon name='circle notched' loading />
      <Message.Content>
        Saving port.
      </Message.Content>
    </Message>
    );
  }

  render() {
    if(this.state.isSaving) {
      return this.renderSpinner()
    }

    return (
      <Form error onSubmit={this.submitAction}>
        <Segment.Group>
          <Segment>
            {this.state.hasError && (
              <Message error content='A name and port is required'/>
            )}

            <Form.Field>
              <label>Name</label>
              <input 
                id="conn_name" 
                placeholder="Connection name" 
                defaultValue={this.state.port}
                onChange={(e) => {this.setState({name: e.target.value})}}
              />
            </Form.Field>

            <Form.Field>
              <Form.Select
                fluid
                label="Port"
                options={this.portOptions()}
                placeholder='Select Port'
                onChange={(e, element) => {this.setState({port: element.value})}}
              />
            </Form.Field>

            <Form.Field>
              <Form.Select
                fluid
                label="Baudrate"
                options={this.baudrateOptions()}
                placeholder='Select Baudrate'
                onChange={(e, element) => {this.setState({baudrate: element.value})}}
              />
            </Form.Field>
          </Segment>

          <Segment textAlign='right'>
            <Button basic onClick={this.cancelAction}>Cancel</Button>
            <Button type='submit' color='green'>Save</Button>
          </Segment>
        </Segment.Group>
      </Form>
    )
  }
}
