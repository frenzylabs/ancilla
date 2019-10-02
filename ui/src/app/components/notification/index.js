//
//  index.js
//  ancilla
// 
//  Created by Wess Cope (me@wess.io) on 10/02/19
//  Copyright 2019 Wess Cope
//

import React      from 'react'
import {connect}  from 'react-redux'

import {
  Message
} from 'semantic-ui-react'

import types    from '../../store/actions/types'
import actions  from '../../store/actions/notification'

class Notification extends React.Component {
  constructor(props) {
    super(props)

    this.dismissAction      = this.dismissAction.bind(this)
    this.generateProperties = this.generateProperties.bind(this)
  }

  dismissAction() {
    this.props.dispatch(actions.dismiss())
  }

  generateProperties() {
    var props = {
      floating:   true,
      id:         'notification-element',
      attached:   'top',
      onDismiss:  this.dismissAction
    }

    if(this.props.details == null) {
      delete props['color']
      delete props['data-notification-type']

      props['hidden'] = true

      return props
    }

    console.log("type: ", this.props.details)
    props['data-notification-type'] = this.props.details.type

    switch(this.props.details.type) {
      case types.notification.warning:
        props['color'] = 'yellow'
      case types.notification.success:
        props['color'] = 'green'
      case types.notification.failure:
        props['color'] = 'red'
      case types.notification.info:
        props['color'] = 'blue'
    }

    return props
  }

  componentDidMount() {
    setTimeout(() => {
      this.dismissAction()
    }, 6000)
  }

  render() {
    return (
      <Message {...this.generateProperties()}>
        {this.props.details && this.props.details.payload &&
          <Message.Header style={{textAlign: 'center'}}>{this.props.details.payload}</Message.Header>
        }
      </Message>
    )
  }
}

const mapStateToProps = (state) => {
  return {
    details: state.notification.notification
  }
}

export default connect(mapStateToProps)(Notification)
