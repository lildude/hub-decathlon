import React from 'react'
import ReactDOM from 'react-dom'

import RuleList from './components/ruleList'

class AerobiaConfig extends React.Component {
    render() {
        return (
            <div className="content">
            <p>Настройка инвентаря по умолчанию</p>
            <RuleList data={[{key: "1"},{key: "2"},{key: "3"}]}/>
            </div>
        );
    }
}

ReactDOM.render(
    React.createElement(AerobiaConfig, window.props),
    window.react_mount,
)