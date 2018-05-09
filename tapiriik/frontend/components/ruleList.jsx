import React from 'react'
import RuleLine from './ruleLine'

export default class RuleList extends React.Component {
    constructor(props) {
        super(props)
        this.state = {
            rules: props.data
        }
    }

    handleNewRule = (event) => {
        var timestamp = (new Date()).getTime();
        this.state.rules.push({
            id: timestamp
        });
        this.setState({ rules: this.state.rules });
        console.log('Rule added');
        event.preventDefault();
    }

    deleteRule(id) {
        this.setState(prevState => ({
            rules: prevState.rules.filter(e => e.id != id)
        }));
        console.log('Rule deleted');
    }

    render() {
        const { sportTypes, gears } = this.props
        var ruleLines = this.state.rules.map(function (rule) {
            return (
                <RuleLine 
                    key={rule.id} 
                    data={rule}
                    sportTypes={sportTypes}
                    gears={gears}
                    handleDelete={() => this.deleteRule(rule.id)}>
                    {rule.text}
                </RuleLine>
            );
        }.bind(this));
        return (
            <div className="RuleList">
                {ruleLines}
                <button className="addRule" onClick={this.handleNewRule} />
            </div>
        );
    }
}